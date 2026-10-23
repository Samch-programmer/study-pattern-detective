
from database import initialize_database, add_study_session, get_all_sessions
from analytics import prepare_data, get_summary, generate_insights

initialize_database()

add_study_session(
    subject_name="Python",
    session_date="2026-10-23",
    duration_minutes=60,
    study_method="Practice",
    questions_practiced=5,
    quiz_score=80,
    notes="Testing the analytics module"
)

sessions = get_all_sessions()
df = prepare_data(sessions)

print("\n--- Dashboard Summary ---")
print(get_summary(df))

print("\n--- Study Insights ---")
for insight in generate_insights(df):
    print("-", insight)
