
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, time

from database import (
    initialize_database,
    add_study_session,
    get_all_sessions,
    delete_study_session
)

from analytics import (
    prepare_data,
    get_summary,
    get_subject_summary,
    get_weekly_summary,
    get_study_method_summary,
    generate_insights
)


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="Study Pattern Detective",
    page_icon="📚",
    layout="wide"
)

initialize_database()


# ---------------- HELPER FUNCTIONS ----------------

def import_study_data(uploaded_file):
    """Read and validate an uploaded CSV or Excel file."""

    try:
        if uploaded_file.name.lower().endswith(".csv"):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        data.columns = [
            str(column).strip().lower().replace(" ", "_")
            for column in data.columns
        ]

        required_columns = [
            "subject_name",
            "session_date",
            "duration_minutes",
            "study_method"
        ]

        missing_columns = [
            column for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:
            st.error(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )
            return

        optional_defaults = {
            "start_time": None,
            "questions_practiced": 0,
            "quiz_score": None,
            "notes": ""
        }

        for column, default in optional_defaults.items():
            if column not in data.columns:
                data[column] = default

        data["subject_name"] = (
            data["subject_name"].fillna("").astype(str).str.strip()
        )
        data["session_date"] = pd.to_datetime(
            data["session_date"], errors="coerce"
        )
        data["duration_minutes"] = pd.to_numeric(
            data["duration_minutes"], errors="coerce"
        )
        data["questions_practiced"] = pd.to_numeric(
            data["questions_practiced"], errors="coerce"
        ).fillna(0)
        data["quiz_score"] = pd.to_numeric(
            data["quiz_score"], errors="coerce"
        )

        valid_rows = (
            data["subject_name"].ne("")
            & data["session_date"].notna()
            & data["duration_minutes"].notna()
            & data["duration_minutes"].gt(0)
            & data["study_method"].notna()
            & data["study_method"].astype(str).str.strip().ne("")
            & data["questions_practiced"].ge(0)
            & data["questions_practiced"].mod(1).eq(0)
            & (
                data["quiz_score"].isna()
                | data["quiz_score"].between(0, 100)
            )
        )

        valid_data = data.loc[valid_rows].copy()

        if valid_data.empty:
            st.error(
                "No valid records found. Check the file's data and format."
            )
            return

        imported_count = 0

        for _, row in valid_data.iterrows():
            session_date = row["session_date"].date().isoformat()

            start_time = row["start_time"]
            if pd.isna(start_time) or str(start_time).strip() == "":
                start_time = None
            else:
                start_time = str(start_time)

            score = row["quiz_score"]
            if pd.isna(score):
                score = None
            else:
                score = float(score)

            add_study_session(
                subject_name=row["subject_name"],
                session_date=session_date,
                duration_minutes=int(row["duration_minutes"]),
                study_method=str(row["study_method"]).strip(),
                start_time=start_time,
                questions_practiced=int(row["questions_practiced"]),
                quiz_score=score,
                notes="" if pd.isna(row["notes"]) else str(row["notes"])
            )

            imported_count += 1

        st.success(
            f"Successfully imported {imported_count} study sessions."
        )

        if len(data) > len(valid_data):
            st.warning(
                f"{len(data) - len(valid_data)} invalid rows were skipped."
            )

    except Exception as error:
        st.error(f"Could not import the file: {error}")


# ---------------- SIDEBAR ----------------

st.sidebar.title("Study Pattern Detective")

page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Add Study Session",
        "Import Data",
        "View & Delete Records"
    ]
)

st.sidebar.caption(
    "Track your study habits. Discover your patterns."
)


# ---------------- DASHBOARD ----------------

if page == "Dashboard":

    st.title("Study Pattern Detective")
    st.write(
        "Understand your study habits through data and interactive charts."
    )

    sessions = get_all_sessions()
    df = prepare_data(sessions)

    if df.empty:
        st.info(
            "No study sessions available yet. "
            "Add a session or import a CSV/Excel file to get started."
        )

    else:
        summary = get_summary(df)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Study Hours", summary["total_hours"])
        col2.metric("Total Sessions", summary["total_sessions"])
        col3.metric(
            "Average Session (min)",
            summary["average_session_minutes"]
        )
        col4.metric(
            "Average Quiz Score",
            (
                f'{summary["average_quiz_score"]}%'
                if summary["average_quiz_score"] is not None
                else "N/A"
            )
        )

        st.subheader("Filter Study Records")

        subject_options = sorted(
            df["subject_name"].dropna().unique().tolist()
        )

        selected_subjects = st.multiselect(
            "Select subjects",
            options=subject_options,
            default=subject_options
        )

        filtered_df = df[
            df["subject_name"].isin(selected_subjects)
        ]

        if filtered_df.empty:
            st.warning("No records match the selected subjects.")

        else:
            left, right = st.columns(2)

            with left:
                st.subheader("Study Hours by Subject")

                subject_summary = get_subject_summary(filtered_df)

                figure = px.bar(
                    subject_summary,
                    x="subject_name",
                    y="study_hours",
                    color="subject_name",
                    labels={
                        "subject_name": "Subject",
                        "study_hours": "Study Hours"
                    },
                    title="Subject-wise Study Time"
                )

                st.plotly_chart(figure, use_container_width=True)

            with right:
                st.subheader("Weekly Study Progress")

                weekly_summary = get_weekly_summary(filtered_df)

                if not weekly_summary.empty:
                    figure = px.line(
                        weekly_summary,
                        x="week_start",
                        y="study_hours",
                        markers=True,
                        labels={
                            "week_start": "Week Starting",
                            "study_hours": "Study Hours"
                        },
                        title="Weekly Study Hours"
                    )

                    st.plotly_chart(
                        figure, use_container_width=True
                    )

            left, right = st.columns(2)

            with left:
                st.subheader("Study Method Analysis")

                method_summary = get_study_method_summary(filtered_df)

                figure = px.pie(
                    method_summary,
                    names="study_method",
                    values="study_hours",
                    title="Distribution of Study Time"
                )

                st.plotly_chart(figure, use_container_width=True)

            with right:
                st.subheader("Quiz Score Analysis")

                scores_df = filtered_df.dropna(subset=["quiz_score"])

                if not scores_df.empty:
                    figure = px.scatter(
                        scores_df,
                        x="duration_minutes",
                        y="quiz_score",
                        color="subject_name",
                        hover_data=["session_date", "study_method"],
                        labels={
                            "duration_minutes": "Study Duration (minutes)",
                            "quiz_score": "Quiz Score (%)"
                        },
                        title="Study Duration vs Quiz Score"
                    )

                    st.plotly_chart(
                        figure, use_container_width=True
                    )
                else:
                    st.info(
                        "Add quiz scores to see this analysis."
                    )

            st.subheader("Study Insights")

            for insight in generate_insights(filtered_df):
                st.write(f"- {insight}")

            st.subheader("Recent Study Sessions")

            display_df = filtered_df[
                [
                    "session_date",
                    "subject_name",
                    "duration_minutes",
                    "study_method",
                    "questions_practiced",
                    "quiz_score"
                ]
            ].copy()

            display_df["session_date"] = (
                display_df["session_date"].dt.strftime("%Y-%m-%d")
            )

            st.dataframe(
                display_df.head(10),
                use_container_width=True,
                hide_index=True
            )


# ---------------- ADD STUDY SESSION ----------------

elif page == "Add Study Session":

    st.title("Add a Study Session")

    with st.form("study_session_form"):

        subject_name = st.text_input(
            "Subject Name",
            placeholder="e.g. Python, DBMS, Machine Learning"
        )

        session_date = st.date_input(
            "Study Date",
            value=date.today(),
            max_value=date.today()
        )

        start_time = st.time_input(
            "Start Time",
            value=time(9, 0)
        )

        duration_minutes = st.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=1440,
            value=60
        )

        study_method = st.selectbox(
            "Study Method",
            [
                "Reading",
                "Practice",
                "Video Lecture",
                "Revision",
                "Project Work",
                "Other"
            ]
        )

        questions_practiced = st.number_input(
            "Questions Practiced",
            min_value=0,
            max_value=100000,
            value=0
        )

        quiz_score_input = st.number_input(
            "Quiz Score (%) — enter -1 if not available",
            min_value=-1.0,
            max_value=100.0,
            value=-1.0,
            step=1.0
        )

        notes = st.text_area(
            "Notes",
            placeholder="What did you learn in this session?"
        )

        submitted = st.form_submit_button(
            "Save Study Session",
            use_container_width=True
        )

        if submitted:
            if not subject_name.strip():
                st.error("Please enter a subject name.")

            else:
                quiz_score = (
                    None if quiz_score_input == -1
                    else quiz_score_input
                )

                try:
                    add_study_session(
                        subject_name=subject_name,
                        session_date=session_date.isoformat(),
                        start_time=start_time.strftime("%H:%M"),
                        duration_minutes=int(duration_minutes),
                        study_method=study_method,
                        questions_practiced=int(questions_practiced),
                        quiz_score=quiz_score,
                        notes=notes.strip()
                    )

                    st.success("Study session saved successfully!")

                except Exception as error:
                    st.error(f"Could not save the session: {error}")


# ---------------- IMPORT DATA ----------------

elif page == "Import Data":

    st.title("Import Study Data")

    st.write(
        "Upload a CSV or Excel file containing your study sessions."
    )

    st.markdown(
        """
        **Required columns:**
        - `subject_name`
        - `session_date`
        - `duration_minutes`
        - `study_method`

        **Optional columns:**
        - `start_time`
        - `questions_practiced`
        - `quiz_score`
        - `notes`
        """
    )

    st.caption(
        "Use dates such as 2026-10-23, positive study durations, "
        "and quiz scores between 0 and 100."
    )

    uploaded_file = st.file_uploader(
        "Choose CSV or Excel file",
        type=["csv", "xlsx"]
    )

    if uploaded_file is not None:
        if st.button("Import Study Data"):
            import_study_data(uploaded_file)


# ---------------- VIEW AND DELETE RECORDS ----------------

elif page == "View & Delete Records":

    st.title("Study Session Records")

    sessions = get_all_sessions()

    if not sessions:
        st.info("No records available yet.")

    else:
        records_df = pd.DataFrame(sessions)

        st.dataframe(
            records_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Delete a Study Session")

        session_ids = records_df["session_id"].tolist()

        selected_id = st.selectbox(
            "Select Session ID",
            options=session_ids
        )

        confirm_delete = st.checkbox(
            "I confirm that I want to delete this session."
        )

        if st.button("Delete Selected Session", type="primary"):
            if confirm_delete:
                delete_study_session(int(selected_id))
                st.success("Study session deleted.")
                st.rerun()
            else:
                st.warning("Please confirm before deleting.")
                
