from django.conf import settings
from google import genai

from ..models import QuizResult, Question, StudentAnswer


# =========================================================
# GEMINI CLIENT
# =========================================================

def get_gemini_client():

    return genai.Client(
        api_key=settings.GEMINI_API_KEY
    )


# =========================================================
# PERSONALIZED RECOMMENDATIONS
# =========================================================

def generate_recommendations(weaknesses):

    if not weaknesses:

        return (
            "1. Continue practising mixed-topic questions to "
            "maintain your current performance.\n\n"
            "2. Revisit difficult questions occasionally even "
            "when your answers are correct.\n\n"
            "3. Try slightly more challenging problems to "
            "strengthen your understanding."
        )

    weakness_text = "\n".join(
        [
            f"""
Topic: {item['topic']}
Question: {item['question']}
Student Answer: {item['student_answer']}
Correct Answer: {item['correct_answer']}
"""
            for item in weaknesses
        ]
    )

    recommendation_prompt = f"""
You are a school learning mentor for ScoreSkill.

Based ONLY on the student's actual incorrect quiz answers below,
give practical learning recommendations.

Incorrect answers:

{weakness_text}

Rules:

- Do not invent topics.
- Do not invent mistakes.
- Do not claim the student is weak overall.
- Identify the concept involved only when it is reasonably clear.
- Recommend practical study actions.
- Keep the language simple and suitable for a school student.
- Give exactly 3 recommendations.
- Do not mention AI or Gemini.
- Do not use markdown symbols.
- Do not use bullet symbols.
- Use numbered points only.

Return only the 3 numbered recommendations.
"""

    try:

        client = get_gemini_client()

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=recommendation_prompt
        )

        return response.text.strip()

    except Exception as e:

        print(
            "GEMINI RECOMMENDATION ERROR:",
            str(e)
        )

        return (
            "1. Review the questions you answered incorrectly "
            "and understand the correct method.\n\n"
            "2. Practise a few similar problems from the "
            "topics where mistakes occurred.\n\n"
            "3. Reattempt a short quiz after reviewing the "
            "concepts to check your improvement."
        )


# =========================================================
# AI PERFORMANCE FEEDBACK
# =========================================================

def generate_ai_feedback(user, analytics):

    total_score = analytics["score"]
    total_possible = analytics["total_possible"]
    percentage = analytics["percentage"]
    level = analytics["level"]

    answer_details = []

    results = QuizResult.objects.filter(
        student=user
    ).select_related("quiz")

    for result in results:

        quiz = result.quiz

        questions = Question.objects.filter(
            quiz=quiz
        )

        for question in questions:

            # Get the latest answer for this question.
            # Using -id avoids problems if the student
            # has attempted the same quiz more than once.

            answer = StudentAnswer.objects.filter(
                student=user,
                question=question
            ).order_by("-id").first()

            if not answer:
                continue

            answer_details.append(
                f"""
Quiz: {quiz.title}
Question: {question.question}
Student Answer: {answer.selected_answer}
Correct Answer: {question.correct_answer}
"""
            )

    performance_data = "\n".join(answer_details)

    prompt = f"""
You are a helpful school learning mentor for ScoreSkill.

Analyze the student's actual quiz performance.

Overall Score:
{total_score} / {total_possible}

Overall Percentage:
{percentage}%

Performance Level:
{level}

Here are the student's actual answers:

{performance_data}

Give a short, useful learning review.

Your response MUST contain these four sections:

Assessment of Performance

Strengths and Positive Observations

Areas for Improvement

Practical Study Recommendations

Rules:

- Base your observations ONLY on the quiz answers provided.
- Identify the questions the student got wrong.
- Explain the concept or type of mistake involved when it is reasonably clear.
- Mention correct answers as strengths when appropriate.
- Do not invent subjects, topics, mistakes or weaknesses.
- If the student answered everything correctly, clearly say that there are no specific weaknesses identified from these quizzes.
- Give exactly two strengths or positive observations when the available data supports them.
- Give exactly two areas for improvement when there are mistakes to discuss.
- Give exactly three practical study recommendations.
- Keep the language simple and suitable for a school student.
- Do not mention AI or Gemini.
- Do not use markdown symbols such as ** or ##.
- Do not use markdown tables.
- Do not use bullet symbols such as *.
- Use simple headings and numbered points.
"""

    try:

        client = get_gemini_client()

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:

        print(
            "GEMINI AI INSIGHTS ERROR:",
            str(e)
        )

        return (
            "AI feedback is temporarily unavailable. "
            "Please try again later."
        )