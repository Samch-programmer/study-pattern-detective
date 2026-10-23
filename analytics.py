
import pandas as pd


def prepare_data(sessions):
    """Convert database records into a clean Pandas DataFrame."""

    columns = [
        "session_id",
        "subject_name",
        "session_date",
        "start_time",
        "duration_minutes",
        "study_method",
        "questions_practiced",
        "quiz_score",
        "notes"
    ]

    df = pd.DataFrame(sessions, columns=columns)

    if df.empty:
        return df

    df["session_date"] = pd.to_datetime(
        df["session_date"], errors="coerce"
    )

    df["duration_minutes"] = pd.to_numeric(
        df["duration_minutes"], errors="coerce"
    )

    df["questions_practiced"] = pd.to_numeric(
        df["questions_practiced"], errors="coerce"
    ).fillna(0)

    df["quiz_score"] = pd.to_numeric(
        df["quiz_score"], errors="coerce"
    )

    df["study_hours"] = df["duration_minutes"] / 60

    df["day_name"] = df["session_date"].dt.day_name()

    df["week_start"] = (
        df["session_date"]
        - pd.to_timedelta(df["session_date"].dt.weekday, unit="D")
    )

    return df


def get_summary(df):
    """Calculate the main dashboard statistics."""

    if df.empty:
        return {
            "total_hours": 0,
            "total_sessions": 0,
            "average_session_minutes": 0,
            "average_quiz_score": None,
            "total_questions": 0
        }

    valid_scores = df["quiz_score"].dropna()

    return {
        "total_hours": round(df["study_hours"].sum(), 2),
        "total_sessions": len(df),
        "average_session_minutes": round(
            df["duration_minutes"].mean(), 2
        ),
        "average_quiz_score": (
            round(valid_scores.mean(), 2)
            if not valid_scores.empty
            else None
        ),
        "total_questions": int(df["questions_practiced"].sum())
    }


def get_subject_summary(df):
    """Calculate study hours and sessions for each subject."""

    if df.empty:
        return pd.DataFrame(
            columns=["subject_name", "study_hours", "total_sessions"]
        )

    summary = (
        df.groupby("subject_name", as_index=False)
        .agg(
            study_hours=("study_hours", "sum"),
            total_sessions=("session_id", "count")
        )
    )

    summary["study_hours"] = summary["study_hours"].round(2)

    return summary.sort_values(
        "study_hours", ascending=False
    )


def get_weekly_summary(df):
    """Calculate total study hours for each week."""

    if df.empty:
        return pd.DataFrame(
            columns=["week_start", "study_hours"]
        )

    summary = (
        df.groupby("week_start", as_index=False)
        .agg(study_hours=("study_hours", "sum"))
        .sort_values("week_start")
    )

    summary["study_hours"] = summary["study_hours"].round(2)

    return summary


def get_study_method_summary(df):
    """Compare study time across different study methods."""

    if df.empty:
        return pd.DataFrame(
            columns=["study_method", "study_hours"]
        )

    summary = (
        df.groupby("study_method", as_index=False)
        .agg(study_hours=("study_hours", "sum"))
    )

    summary["study_hours"] = summary["study_hours"].round(2)

    return summary.sort_values(
        "study_hours", ascending=False
    )


def generate_insights(df):
    """Generate simple insights from the student's study history."""

    if df.empty:
        return [
            "No study records found yet. Add your first study session!"
        ]

    insights = []

    total_hours = df["study_hours"].sum()
    insights.append(
        f"You have studied for {total_hours:.2f} hours in total."
    )

    subject_summary = get_subject_summary(df)

    if not subject_summary.empty:
        top_subject = subject_summary.iloc[0]

        insights.append(
            f"Your most-studied subject is "
            f"{top_subject['subject_name']} "
            f"with {top_subject['study_hours']:.2f} hours."
        )

    valid_scores = df.dropna(subset=["quiz_score"])

    if not valid_scores.empty:
        average_score = valid_scores["quiz_score"].mean()

        insights.append(
            f"Your average recorded quiz score is "
            f"{average_score:.2f}%."
        )

    daily_hours = (
        df.groupby(df["session_date"].dt.date)["study_hours"].sum()
    )

    if not daily_hours.empty:
        best_day = daily_hours.idxmax()

        insights.append(
            f"Your highest recorded study time was on "
            f"{best_day}: {daily_hours.max():.2f} hours."
        )

    return insights
