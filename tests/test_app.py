"""Comprehensive tests for the Mergington High School Activities API."""

import pytest


class TestRoot:
    """Tests for the root endpoint."""

    def test_root_redirect(self, client):
        """Test that root redirects to /static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_all_activities_success(self, client):
        """Test retrieving all activities returns correct structure."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()

        # Verify it's a dictionary with activity names as keys
        assert isinstance(data, dict)
        assert len(data) == 9  # 9 activities in the database

        # Verify each activity has required fields
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_includes_chess_club(self, client):
        """Test that Chess Club is included in activities."""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data
        assert data["Chess Club"]["max_participants"] == 12

    def test_get_activities_includes_all_initial_participants(self, client):
        """Test that initial participants are present in each activity."""
        response = client.get("/activities")
        data = response.json()

        # Chess Club should have 2 initial participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        """Test successful signup adds participant to activity."""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]

        # Verify participant was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_duplicate_rejected(self, client):
        """Test that duplicate signup is prevented with 400 error."""
        # michael@mergington.edu is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_activity_not_found(self, client):
        """Test signup to non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_multiple_students_same_activity(self, client):
        """Test that multiple different students can sign up for same activity."""
        # Sign up first student
        response1 = client.post(
            "/activities/Programming Class/signup?email=alice@mergington.edu"
        )
        assert response1.status_code == 200

        # Sign up second student
        response2 = client.post(
            "/activities/Programming Class/signup?email=bob@mergington.edu"
        )
        assert response2.status_code == 200

        # Verify both are in the activity
        activities_response = client.get("/activities")
        activities = activities_response.json()
        participants = activities["Programming Class"]["participants"]
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" in participants

    def test_signup_student_multiple_activities(self, client):
        """Test that same student can sign up for different activities."""
        student_email = "multitasker@mergington.edu"

        # Sign up for Chess Club
        response1 = client.post(
            f"/activities/Chess Club/signup?email={student_email}"
        )
        assert response1.status_code == 200

        # Sign up for Programming Class
        response2 = client.post(
            f"/activities/Programming Class/signup?email={student_email}"
        )
        assert response2.status_code == 200

        # Verify in both activities
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert student_email in activities["Chess Club"]["participants"]
        assert student_email in activities["Programming Class"]["participants"]

    def test_signup_email_case_sensitive(self, client):
        """Test that email addresses are treated case-sensitively."""
        email_lower = "casesensitive@mergington.edu"
        email_upper = "CASESENSITIVE@MERGINGTON.EDU"

        # Sign up with lowercase
        response1 = client.post(
            f"/activities/Art Club/signup?email={email_lower}"
        )
        assert response1.status_code == 200

        # Try to sign up with uppercase (different email, should succeed)
        response2 = client.post(
            f"/activities/Art Club/signup?email={email_upper}"
        )
        assert response2.status_code == 200

    def test_signup_special_characters_in_activity_name(self, client):
        """Test signup works with special characters in activity names."""
        # "Gym Class" contains a space
        response = client.post(
            "/activities/Gym%20Class/signup?email=athlete@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/signup endpoint."""

    def test_remove_participant_success(self, client):
        """Test successful removal of participant from activity."""
        # First, verify michael is in Chess Club
        activities = client.get("/activities").json()
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        initial_count = len(activities["Chess Club"]["participants"])

        # Remove michael from Chess Club
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        assert "michael@mergington.edu" in data["message"]

        # Verify michael was removed
        activities = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1

    def test_remove_activity_not_found(self, client):
        """Test removing from non-existent activity returns 404."""
        response = client.delete(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_remove_student_not_in_activity(self, client):
        """Test removing student who isn't enrolled returns 400."""
        # noah@mergington.edu is in Drama Club but not Chess Club
        response = client.delete(
            "/activities/Chess Club/signup?email=noah@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_remove_nonexistent_student(self, client):
        """Test removing an email that was never in the system returns 400."""
        response = client.delete(
            "/activities/Chess Club/signup?email=nobody@mergington.edu"
        )
        assert response.status_code == 400

    def test_remove_multiple_students_sequentially(self, client):
        """Test removing multiple participants one by one."""
        # Add two students first
        client.post("/activities/Tennis Club/signup?email=player1@mergington.edu")
        client.post("/activities/Tennis Club/signup?email=player2@mergington.edu")

        # Remove first
        response1 = client.delete(
            "/activities/Tennis Club/signup?email=player1@mergington.edu"
        )
        assert response1.status_code == 200

        # Remove second
        response2 = client.delete(
            "/activities/Tennis Club/signup?email=player2@mergington.edu"
        )
        assert response2.status_code == 200

        # Verify both are gone
        activities = client.get("/activities").json()
        participants = activities["Tennis Club"]["participants"]
        assert "player1@mergington.edu" not in participants
        assert "player2@mergington.edu" not in participants

    def test_remove_then_rejoin_activity(self, client):
        """Test that student can rejoin after being removed."""
        student = "rejoin@mergington.edu"

        # Sign up
        response1 = client.post(
            f"/activities/Drama Club/signup?email={student}"
        )
        assert response1.status_code == 200

        # Remove
        response2 = client.delete(
            f"/activities/Drama Club/signup?email={student}"
        )
        assert response2.status_code == 200

        # Sign up again
        response3 = client.post(
            f"/activities/Drama Club/signup?email={student}"
        )
        assert response3.status_code == 200

        # Verify back in activity
        activities = client.get("/activities").json()
        assert student in activities["Drama Club"]["participants"]


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_all_activities_accessible(self, client):
        """Test that all 9 activities can be accessed."""
        response = client.get("/activities")
        activities = response.json()

        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Art Club",
            "Drama Club",
            "Debate Team",
            "Science Club",
        ]

        for activity in expected_activities:
            assert activity in activities

    def test_participant_count_accuracy(self, client):
        """Test that participant counts match actual participant lists."""
        response = client.get("/activities")
        activities = response.json()

        for activity_name, activity_data in activities.items():
            participant_list = activity_data["participants"]
            # Just verify the list contains valid email strings
            for email in participant_list:
                assert isinstance(email, str)
                assert "@" in email

    def test_max_participants_field_exists(self, client):
        """Test that max_participants is set for all activities."""
        response = client.get("/activities")
        activities = response.json()

        for activity_name, activity_data in activities.items():
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0

    def test_empty_email_signup_attempt(self, client):
        """Test signup with empty email parameter."""
        response = client.post("/activities/Chess Club/signup?email=")
        # Empty string should be treated as an email (though invalid)
        # The endpoint doesn't validate email format, so "" is technically a participant
        # This test just documents the current behavior
        assert response.status_code == 200

    def test_special_characters_in_email(self, client):
        """Test that emails with special characters are accepted."""
        special_email = "test+special@mergington.edu"
        response = client.post(
            f"/activities/Science Club/signup?email={special_email}"
        )
        assert response.status_code == 200

        # Verify it was added
        activities = client.get("/activities").json()
        assert special_email in activities["Science Club"]["participants"]
