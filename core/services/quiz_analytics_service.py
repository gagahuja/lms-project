from core.models import QuizResult, Question, StudentAnswer


def get_quiz_analytics(user):
    """
    Build all quiz-performance analytics for a student.

    This service contains the calculation logic previously
    handled inside the ai_insights view.
    """

    # =========================================================
    # QUIZ RESULTS
    # =========================================================

    results = QuizResult.objects.filter(
        student=user
    ).select_related("quiz")


    # =========================================================
    # OVERALL PERFORMANCE
    # =========================================================

    total_score = sum(
        result.score
        for result in results
    )

    total_possible = sum(
        result.total
        for result in results
    )

    if total_possible > 0:

        percentage = round(
            (total_score / total_possible) * 100,
            1
        )

    else:

        percentage = 0


    # =========================================================
    # PERFORMANCE LEVEL
    # =========================================================

    if percentage >= 75:

        level = "Strong"

    elif percentage >= 50:

        level = "Average"

    else:

        level = "Weak"


    # =========================================================
    # QUIZ PERFORMANCE TREND
    # =========================================================

    trend_results = results.order_by("id")

    performance_trend = []

    for result in trend_results:

        if result.total > 0:

            result_percentage = round(
                (result.score / result.total) * 100,
                1
            )

        else:

            result_percentage = 0

        performance_trend.append({
            "title": result.quiz.title,
            "score": result.score,
            "total": result.total,
            "percentage": result_percentage,
        })


    # =========================================================
    # QUIZ PERFORMANCE HISTORY
    # =========================================================

    quiz_history = []

    for result in results:

        if result.total > 0:

            result_percentage = round(
                (result.score / result.total) * 100,
                1
            )

        else:

            result_percentage = 0


        if result_percentage >= 75:

            result_level = "Strong"

        elif result_percentage >= 50:

            result_level = "Average"

        else:

            result_level = "Weak"


        quiz_history.append({
            "title": result.quiz.title,
            "score": result.score,
            "total": result.total,
            "percentage": result_percentage,
            "level": result_level,
        })


    # =========================================================
    # TOPIC PERFORMANCE
    # =========================================================

    topic_data = {}

    for result in results:

        topic = result.quiz.title

        # Remove "AI Quiz -" from generated quiz titles
        if topic.lower().startswith("ai quiz -"):

            topic = topic[9:].strip()


        if topic not in topic_data:

            topic_data[topic] = {
                "score": 0,
                "total": 0,
                "attempts": 0,
            }


        topic_data[topic]["score"] += result.score

        topic_data[topic]["total"] += result.total

        topic_data[topic]["attempts"] += 1


    topic_performance = []


    for topic, data in topic_data.items():

        if data["total"] > 0:

            topic_percentage = round(
                (data["score"] / data["total"]) * 100,
                1
            )

        else:

            topic_percentage = 0


        if topic_percentage >= 75:

            topic_level = "Strong"

        elif topic_percentage >= 50:

            topic_level = "Average"

        else:

            topic_level = "Needs Attention"


        topic_performance.append({

            "topic": topic,

            "score": data["score"],

            "total": data["total"],

            "percentage": topic_percentage,

            "attempts": data["attempts"],

            "level": topic_level,

        })


    # =========================================================
    # STRONGEST TOPIC
    # =========================================================

    strongest_topic = None

    if topic_performance:

        strongest_topic = max(
            topic_performance,
            key=lambda x: x["percentage"]
        )


    # =========================================================
    # WEAKEST TOPIC
    # =========================================================

    weakest_topic = None

    if topic_performance:

        weakest_topic = min(
            topic_performance,
            key=lambda x: x["percentage"]
        )


    # =========================================================
    # WEAKNESS DETECTION
    # =========================================================

    weaknesses = []

    student_results = results.order_by("id")


    for result in student_results:

        quiz = result.quiz

        questions = Question.objects.filter(
            quiz=quiz
        )


        for question in questions:

            # Get the latest answer for this question
            answer = StudentAnswer.objects.filter(
                student=user,
                question=question
            ).order_by("-id").first()


            if not answer:

                continue


            # Only analyse incorrect answers
            if answer.selected_answer != question.correct_answer:

                topic = quiz.title


                if topic.lower().startswith("ai quiz -"):

                    topic = topic[9:].strip()


                weaknesses.append({

                    "topic": topic,

                    "question": question.question,

                    "student_answer":
                        answer.selected_answer,

                    "correct_answer":
                        question.correct_answer,

                })


    # =========================================================
    # FOCUS TOPICS
    # =========================================================

    focus_topics = []

    for item in topic_performance:

        # Topics below 85% are worth reviewing

        if item["percentage"] < 85:

            focus_topics.append(item)


    # =========================================================
    # RETURN ALL ANALYTICS
    # =========================================================

    return {

        "score": total_score,

        "total_possible": total_possible,

        "percentage": percentage,

        "level": level,

        "quiz_history": quiz_history,

        "performance_trend":
            performance_trend,

        "topic_performance":
            topic_performance,

        "strongest_topic":
            strongest_topic,

        "weakest_topic":
            weakest_topic,

        "weaknesses":
            weaknesses,

        "focus_topics":
            focus_topics,

    }