import streamlit as st
import pandas as pd
import random
import os
import matplotlib.pyplot as plt
import sqlite3

# SQLite 데이터베이스 설정
conn = sqlite3.connect('progress.db')
c = conn.cursor()

# 테이블 생성
c.execute('''
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY,
    last_day INTEGER,
    progress_data TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS incorrect_notes (
    id INTEGER PRIMARY KEY,
    day INTEGER,
    meaning TEXT,
    user_answer TEXT,
    correct_answer TEXT
)
''')

conn.commit()

# 사용자 진행 상태 불러오기
c.execute("SELECT last_day FROM progress WHERE id = 1")
result = c.fetchone()

if result:
    last_day = result[0]
else:
    last_day = 1
    c.execute("INSERT INTO progress (id, last_day) VALUES (1, ?)", (last_day,))
    conn.commit()

# 현재 학습 일자 결정
if 'day' not in st.session_state:
    st.session_state.day = last_day

day = st.session_state.day

# CSV 파일 로드
file_path = 'words.csv'  # CSV 파일 경로
words_df = pd.read_csv(file_path)

# 설정: 하루에 외울 단어 수
words_per_day = 20

# 학습 일자에 따른 인덱스 범위 계산
def get_words_index(day, words_per_day):
    start_idx = (day - 1) * words_per_day
    end_idx = start_idx + words_per_day
    return start_idx, end_idx

# 전날 학습한 단어 중 랜덤으로 10개 선택
def get_review_words(words, review_count=10):
    # 복습 문제를 한 번만 선택하고 이후에는 고정된 문제 세트를 사용
    if f'review_words_day_{day}' not in st.session_state:
        st.session_state[f'review_words_day_{day}'] = words.sample(review_count).reset_index(drop=True)
    return st.session_state[f'review_words_day_{day}']

# 오늘의 단어 인덱스 범위 계산
start_idx, end_idx = get_words_index(day, words_per_day)

# 오늘의 단어들 선택
today_words = words_df.iloc[start_idx:end_idx]

# 복습용 단어 추가 (Day 2부터)
if day > 1:
    previous_day_words = words_df.iloc[get_words_index(day-1, words_per_day)[0]:get_words_index(day-1, words_per_day)[1]]
    review_words = get_review_words(previous_day_words)
    today_words = pd.concat([today_words, review_words]).reset_index(drop=True)

# 오답 노트 저장
def save_incorrect_answers(day, incorrect_answers):
    for meaning, user_answer, correct_word in incorrect_answers:
        c.execute('''
            INSERT INTO incorrect_notes (day, meaning, user_answer, correct_answer)
            VALUES (?, ?, ?, ?)
        ''', (day, meaning, user_answer, correct_word))
    conn.commit()

# 오답 노트 로드
def load_incorrect_answers(day):
    c.execute("SELECT meaning, user_answer, correct_answer FROM incorrect_notes WHERE day = ?", (day,))
    result = c.fetchall()
    if result:
        return pd.DataFrame(result, columns=['Meaning', 'Your Answer', 'Correct Answer'])
    else:
        return None

# 성취도 기록 저장
def save_progress(day, score, total):
    c.execute('''
        UPDATE progress
        SET last_day = ?
        WHERE id = 1
    ''', (day,))
    conn.commit()

# 성취도 그래프 시각화
def plot_progress():
    if 'progress' in st.session_state:
        days = sorted(st.session_state.progress.keys())
        scores = [st.session_state.progress[day]['score'] for day in days]
        totals = [st.session_state.progress[day]['total'] for day in days]
        
        plt.figure(figsize=(10, 5))
        plt.bar(days, scores, color='green')
        plt.plot(days, totals, color='blue', marker='o', linestyle='--')
        plt.xlabel('Day')
        plt.ylabel('Score')
        plt.title('성취도 그래프')
        plt.ylim(0, max(totals) + 5)
        plt.xticks(days)
        plt.yticks(range(0, max(totals) + 1, 5))
        st.pyplot(plt)

# 테스트 실행
def run_test(words):
    score = 0
    incorrect_answers = []

    for index, row in words.iterrows():
        meaning = row['meaning']  # 한국어 뜻 (문제)
        correct_word = row['word']  # 정답 (영어 단어)

        # 문제(뜻)를 표시하고, 사용자로부터 답변(영어 단어)을 입력받음
        user_answer = st.text_input(f"{meaning}", key=f"word_{day}_{index}")  # 각 Day별로 고유한 key 설정

        if st.button(f"제출-{day}-{index}"):  # 제출 버튼
            if user_answer.lower() == correct_word.lower():
                st.write("정답!")
                score += 1
            else:
                st.write(f"오답! 다시 생각해보세요.")
                incorrect_answers.append((meaning, user_answer, correct_word))

    return incorrect_answers, score, len(words)

# 메인 프로그램
st.title("영어 단어 테스트 for 준혁")

if not today_words.empty:
    st.write(f"오늘은 Day {day}에 대한 학습입니다.")
    incorrect_answers, score, total = run_test(today_words)

    if st.button("결과 확인"):
        st.write(f"총 {total} 문제 중 {score} 문제 맞췄습니다.")
        
        if incorrect_answers:
            st.write("오답 노트:")
            for meaning, user_answer, correct_word in incorrect_answers:
                st.write(f"{meaning}: 당신의 답변 - '{user_answer}', 정답 - '{correct_word}'")
            save_incorrect_answers(day, incorrect_answers)
        
        # 오답노트 확인 후에만 "다음 Day로 이동" 버튼 표시
        if st.button("다음 Day로 이동"):
            # 성취도 저장 및 다음 Day로 이동
            save_progress(day + 1, score, total)
            st.session_state.day += 1
            st.experimental_rerun()  # 페이지를 새로고침하여 Day 이동을 반영

# 이전 Day로 이동 버튼 추가
if st.button("이전 Day로 이동") and day > 1:
    st.session_state.day -= 1
    st.experimental_rerun()  # 페이지를 새로고침하여 Day 이동을 반영

# 성취도 그래프 시각화
st.write("성취도 그래프를 확인하세요:")
plot_progress()

# 오답 노트 열람
st.write("이전 학습 일자의 오답 노트를 확인하세요:")
days_with_notes = c.execute("SELECT DISTINCT day FROM incorrect_notes").fetchall()
for past_day in days_with_notes:
    if st.button(f"Day {past_day[0]} 오답 노트 보기"):
        incorrect_df = load_incorrect_answers(past_day[0])
        if incorrect_df is not None:
            st.write(incorrect_df)
        else:
            st.write(f"Day {past_day[0]}에 대한 오답 노트가 없습니다.")

conn.close()
