import streamlit as st
import pandas as pd
import random
import os
import matplotlib.pyplot as plt

# CSV 파일 로드
def load_words(file_path):
    return pd.read_csv(file_path)

# 학습 일자에 따른 인덱스 범위 계산
def get_words_index(day, words_per_day):
    start_idx = (day - 1) * words_per_day
    end_idx = start_idx + words_per_day
    return start_idx, end_idx

# 전날 학습한 단어 중 랜덤으로 10개 선택
def get_review_words(words, review_count=10):
    if len(words) > review_count:
        return words.sample(review_count)
    return words

# 오답 노트 저장
def save_incorrect_answers(day, incorrect_answers):
    file_path = f"incorrect_day_{day}.csv"
    df = pd.DataFrame(incorrect_answers, columns=['Meaning', 'Your Answer', 'Correct Answer'])
    df.to_csv(file_path, index=False)

# 오답 노트 로드
def load_incorrect_answers(day):
    file_path = f"incorrect_day_{day}.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return None

# 성취도 기록 저장
def save_progress(day, score, total):
    if 'progress' not in st.session_state:
        st.session_state.progress = {}
    
    st.session_state.progress[day] = {
        'score': score,
        'total': total
    }

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
        meaning = row['meaning']
        correct_word = row['word']
        user_answer = st.text_input(f"'{meaning}'", key=f"word_{index}")

        if st.button(f"제출-{index}"):
            if user_answer.lower() == correct_word.lower():
                st.write("정답!")
                score += 1
            else:
                st.write(f"오답! 정답은 '{correct_word}'입니다.")
                incorrect_answers.append((meaning, user_answer, correct_word))

    return incorrect_answers, score, len(words)

# 메인 프로그램
st.title("영어 단어 테스트 for 준혁")

# CSV 파일 경로 지정
file_path = 'words.csv'  # CSV 파일 경로
words_df = load_words(file_path)

# 설정: 하루에 외울 단어 수
words_per_day = 20

# 현재 학습 일자 결정
if 'day' not in st.session_state:
    st.session_state.day = 1

day = st.session_state.day

# 오늘의 단어 인덱스 범위 계산
start_idx, end_idx = get_words_index(day, words_per_day)

# 오늘의 단어들 선택
today_words = words_df.iloc[start_idx:end_idx]

# 복습용 단어 추가 (Day 2부터)
if day > 1:
    previous_day_words = words_df.iloc[get_words_index(day-1, words_per_day)[0]:get_words_index(day-1, words_per_day)[1]]
    review_words = get_review_words(previous_day_words)
    today_words = pd.concat([today_words, review_words])

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
        else:
            st.write("오답이 없습니다. 잘했어요!")
        
        # 성취도 저장
        save_progress(day, score, total)
        st.session_state.day += 1  # 다음 날로 이동

# 성취도 그래프 시각화
st.write("성취도 그래프를 확인하세요:")
plot_progress()

# 오답 노트 열람
st.write("이전 학습 일자의 오답 노트를 확인하세요:")
for past_day in range(1, day):
    if st.button(f"Day {past_day} 오답 노트 보기"):
        incorrect_df = load_incorrect_answers(past_day)
        if incorrect_df is not None:
            st.write(incorrect_df)
        else:
            st.write(f"Day {past_day}에 대한 오답 노트가 없습니다.")
