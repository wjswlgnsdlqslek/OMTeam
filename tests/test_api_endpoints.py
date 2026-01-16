import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import date, time, datetime
import json

from app.main import app
from app.api.schemas import (
    DailyMissionResponse, DailyMissionRequest, Mission, MissionType, Difficulty, WorkTimeType, LifestyleType, RecentMissionHistoryItem, MissionResult, OnboardingData,
    DailyFeedbackResponse, DailyFeedbackRequest, TodayMissionData, RecentSummaryData, Intent, EncouragementCandidate,
    WeeklyAnalysisResponse, WeeklyAnalysisRequest, WeekRangeData, WeeklyStatsData, FailureReasonRankedItem,
    ChatSessionResponse, ChatSessionRequest, InitialChatContext, BotMessage, BotMessageOption,
    ChatMessageResponse, ChatMessageRequest, ChatInputType, ChatInput, ChatState
)

client = TestClient(app)

class TestDailyMissionsAPI(unittest.TestCase):
    @patch('api_server.run_agent_system')
    def test_create_daily_missions_success(self, mock_run_agent_system):
        # Mock the agent system's response
        mock_response_content = """
        ```json
        {
            "missions": [
                {
                    "name": "저녁 스트레칭 20분",
                    "type": "EXERCISE",
                    "difficulty": "EASY",
                    "estimatedMinutes": 20,
                    "estimatedCalories": 80
                },
                {
                    "name": "단백질 중심 식단 기록",
                    "type": "DIET",
                    "difficulty": "NORMAL",
                    "estimatedMinutes": 10,
                    "estimatedCalories": 0
                }
            ]
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "planner"}

        # Prepare request payload
        request_payload = {
            "userId": 12345,
            "onboarding": {
                "appGoal": "체중 감량",
                "workTimeType": "FIXED",
                "availableStartTime": "18:30",
                "availableEndTime": "22:00",
                "minExerciseMinutes": 20,
                "preferredExercises": ["러닝", "훌라후프"],
                "lifestyleType": "NIGHT"
            },
            "recentMissionHistory": [
                {
                    "date": "2026-01-08",
                    "missionType": "EXERCISE",
                    "difficulty": "NORMAL",
                    "result": "FAILURE",
                    "failureReason": "시간 부족"
                }
            ],
            "weeklyFailureReasons": ["시간 부족", "동기 부족"]
        }

        # Make the request
        response = client.post("/ai/missions/daily", json=request_payload)

        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("missions", response_data)
        self.assertEqual(len(response_data["missions"]), 2)
        self.assertEqual(response_data["missions"][0]["name"], "저녁 스트레칭 20분")
        self.assertEqual(response_data["missions"][1]["type"], "DIET")
        DailyMissionResponse(**response_data) # Validate with Pydantic model

        # Verify run_agent_system was called correctly (basic check)
        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("사용자 ID: 12345", kwargs["user_request"])

        self.assertIn("preferences", kwargs["user_payload"])
        self.assertEqual(kwargs["user_id"], "12345")


    @patch('api_server.run_agent_system')
    def test_create_daily_missions_ai_response_parse_error(self, mock_run_agent_system):
        # Mock the agent system's response to be invalid JSON
        mock_run_agent_system.return_value = {"agent_response": "This is not JSON", "selected_agent": "planner"}

        request_payload = {
            "userId": 12345,
            "onboarding": {
                "appGoal": "체중 감량",
                "workTimeType": "FIXED",
                "availableStartTime": "18:30",
                "availableEndTime": "22:00",
                "minExerciseMinutes": 20,
                "preferredExercises": [" 러닝", " 훌라후프"],
                "lifestyleType": "NIGHT"
            },
            "recentMissionHistory": [],
            "weeklyFailureReasons": []
        }

        response = client.post("/ai/missions/daily", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to parse AI agent's response as JSON", response.json()["detail"])

    @patch('api_server.run_agent_system')
    def test_create_daily_missions_ai_response_validation_error(self, mock_run_agent_system):
        # Mock the agent system's response to be valid JSON but not conform to schema
        mock_response_content = """
        ```json
        {
            "missions": [
                {
                    "name": "저녁 스트레칭 20분",
                    "type": "INVALID_TYPE", # Invalid type
                    "difficulty": "EASY",
                    "estimatedMinutes": 20,
                    "estimatedCalories": 80
                }
            ]
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "planner"}

        request_payload = {
            "userId": 12345,
            "onboarding": {
                "appGoal": "체중 감량",
                "workTimeType": "FIXED",
                "availableStartTime": "18:30",
                "availableEndTime": "22:00",
                "minExerciseMinutes": 20,
                "preferredExercises": ["러닝", "훌라후프"],
                "lifestyleType": "NIGHT"
            },
            "recentMissionHistory": [],
            "weeklyFailureReasons": []
        }

        response = client.post("/ai/missions/daily", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("AI agent's response did not match the expected DailyMissionResponse schema", response.json()["detail"])

class TestDailyFeedbackAPI(unittest.TestCase):
    @patch('api_server.run_agent_system')
    def test_create_daily_feedback_success(self, mock_run_agent_system):
        # Mock the agent system's response
        mock_response_content = """
        ```json
        {
            "feedbackText": "오늘은 시간 부족으로 미션을 완료하지 못했어",
            "encouragementCandidates": [
                {"intent": "RETRY", "title": "다음은 다시 도전해봐요", "message": "내일은 5분짜리 미션부터 가볍게 시작해봐요."}
            ]
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "analysis"}

        # Prepare request payload
        request_payload = {
            "userId": 12345,
            "targetDate": "2026-01-10",
            "todayMission": {
                "missionType": "EXERCISE",
                "difficulty": "NORMAL",
                "result": "FAILURE",
                "failureReason": "시간 부족"
            },
            "recentSummary": {
                "successDays": 3,
                "failureDays": 2
            }
        }

        # Make the request
        response = client.post("/ai/analysis/daily", json=request_payload)

        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("feedbackText", response_data)
        self.assertIn("encouragementCandidates", response_data)
        self.assertEqual(len(response_data["encouragementCandidates"]), 1)
        self.assertEqual(response_data["encouragementCandidates"][0]["intent"], "RETRY")
        DailyFeedbackResponse(**response_data) # Validate with Pydantic model

        # Verify run_agent_system was called correctly (basic check)
        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("분석 대상 날짜: 2026-01-10", kwargs["user_request"])
        self.assertIn("event", kwargs["user_payload"])
        self.assertEqual(kwargs["user_id"], "12345")

    @patch('api_server.run_agent_system')
    def test_create_daily_feedback_ai_response_parse_error(self, mock_run_agent_system):
        # Mock the agent system's response to be invalid JSON
        mock_run_agent_system.return_value = {"agent_response": "This is not JSON", "selected_agent": "analysis"}

        request_payload = {
            "userId": 12345,
            "targetDate": "2026-01-10",
            "todayMission": {
                "missionType": "EXERCISE",
                "difficulty": "NORMAL",
                "result": "FAILURE",
                "failureReason": "시간 부족"
            },
            "recentSummary": {
                "successDays": 3,
                "failureDays": 2
            }
        }

        response = client.post("/ai/analysis/daily", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to parse AI agent's response as JSON", response.json()["detail"])

    @patch('api_server.run_agent_system')
    def test_create_daily_feedback_ai_response_validation_error(self, mock_run_agent_system):
        # Mock the agent system's response to be valid JSON but not conform to schema
        mock_response_content = """
        ```json
        {
            "feedbackText": "오늘은 시간 부족으로 미션을 완료하지 못했어",
            "encouragementCandidates": [
                {"intent": "INVALID_INTENT", "title": "제목", "message": "메시지"} # Invalid intent type
            ]
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "analysis"}

        request_payload = {
            "userId": 12345,
            "targetDate": "2026-01-10",
            "todayMission": {
                "missionType": "EXERCISE",
                "difficulty": "NORMAL",
                "result": "FAILURE",
                "failureReason": "시간 부족"
            },
            "recentSummary": {
                "successDays": 3,
                "failureDays": 2
            }
        }

        response = client.post("/ai/analysis/daily", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("AI agent's response did not match the expected DailyFeedbackResponse schema", response.json()["detail"])

class TestWeeklyAnalysisAPI(unittest.TestCase):
    @patch('api_server.run_agent_system')
    def test_create_weekly_analysis_success(self, mock_run_agent_system):
        # Mock the agent system's response
        mock_response_content = """
        ```json
        {
            "mainFailureReason": "운동 가능 시간 확보 실패",
            "overallFeedback": "이번 주에는 일정 제약으로 미션 실패가 많았네요. 다음 주에는 시간을 조금 더 확보해보세요."
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "analysis"}

        # Prepare request payload
        request_payload = {
            "userId": 12345,
            "weekRange": {"start": "2026-01-05", "end": "2026-01-11"},
            "weeklyStats": {"totalDays": 7, "successDays": 3, "failureDays": 4},
            "failureReasonsRanked": [
                {"reason": "시간 부족", "count": 3},
                {"reason": "동기 부족", "count": 1}
            ]
        }

        # Make the request
        response = client.post("/ai/analysis/weekly", json=request_payload)

        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("mainFailureReason", response_data)
        self.assertIn("overallFeedback", response_data)
        self.assertEqual(response_data["mainFailureReason"], "운동 가능 시간 확보 실패")
        WeeklyAnalysisResponse(**response_data) # Validate with Pydantic model

        # Verify run_agent_system was called correctly (basic check)
        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("주간 분석 범위: 2026-01-05 ~ 2026-01-11", kwargs["user_request"])
        self.assertIn("event", kwargs["user_payload"])
        self.assertEqual(kwargs["user_id"], "12345")

    @patch('api_server.run_agent_system')
    def test_create_weekly_analysis_ai_response_parse_error(self, mock_run_agent_system):
        # Mock the agent system's response to be invalid JSON
        mock_run_agent_system.return_value = {"agent_response": "This is not JSON", "selected_agent": "analysis"}

        request_payload = {
            "userId": 12345,
            "weekRange": {"start": "2026-01-05", "end": "2026-01-11"},
            "weeklyStats": {"totalDays": 7, "successDays": 3, "failureDays": 4},
            "failureReasonsRanked": []
        }

        response = client.post("/ai/analysis/weekly", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to parse AI agent's response as JSON", response.json()["detail"])

    @patch('api_server.run_agent_system')
    def test_create_weekly_analysis_ai_response_validation_error(self, mock_run_agent_system):
        # Mock the agent system's response to be valid JSON but not conform to schema
        mock_response_content = """
        ```json
        {
            "mainFailureReason": "운동 가능 시간 확보 실패",
            "overallFeedback_INVALID": "This field name is wrong"
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "analysis"}

        request_payload = {
            "userId": 12345,
            "weekRange": {"start": "2026-01-05", "end": "2026-01-11"},
            "weeklyStats": {"totalDays": 7, "successDays": 3, "failureDays": 4},
            "failureReasonsRanked": []
        }

        response = client.post("/ai/analysis/weekly", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("AI agent's response did not match the expected WeeklyAnalysisResponse schema", response.json()["detail"])

class TestChatSessionAPI(unittest.TestCase):
    @patch('api_server.run_agent_system')
    def test_create_chat_session_success(self, mock_run_agent_system):
        # Mock the agent system's response
        mock_response_content = """
        ```json
        {
            "botMessage": {
                "messageId": 5001,
                "text": "안녕하세요! 요즘 운동이나 생활 습관에서 가장 고민되는 부분이 무엇인가요?",
                "options": [
                    {"label": "운동이 너무 힘들어요", "value": "EXERCISE_HARD"},
                    {"label": "식단 관리가 어려워요", "value": "DIET_HARD"}
                ]
            }
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "coach"}

        # Prepare request payload
        request_payload = {
            "sessionId": 1001,
            "userId": 12345,
            "initialContext": {
                "appGoal": "체중 감량",
                "lifestyleType": "NIGHT"
            }
        }

        # Make the request
        response = client.post("/ai/chat/sessions", json=request_payload)

        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("botMessage", response_data)
        self.assertIn("text", response_data["botMessage"])
        self.assertIn("options", response_data["botMessage"])
        self.assertEqual(len(response_data["botMessage"]["options"]), 2)
        ChatSessionResponse(**response_data) # Validate with Pydantic model

        # Verify run_agent_system was called correctly (basic check)
        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("새로운 채팅 세션이 시작되었습니다", kwargs["user_request"])
        self.assertIn("preferences", kwargs["user_payload"])
        self.assertEqual(kwargs["user_id"], "12345")

    @patch('api_server.run_agent_system')
    def test_create_chat_session_ai_response_parse_error(self, mock_run_agent_system):
        # Mock the agent system's response to be invalid JSON
        mock_run_agent_system.return_value = {"agent_response": "This is not JSON", "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1001,
            "userId": 12345,
            "initialContext": {
                "appGoal": "체중 감량",
                "lifestyleType": "NIGHT"
            }
        }

        response = client.post("/ai/chat/sessions", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to parse AI agent's response as JSON", response.json()["detail"])

    @patch('api_server.run_agent_system')
    def test_create_chat_session_ai_response_validation_error(self, mock_run_agent_system):
        # Mock the agent system's response to be valid JSON but not conform to schema
        mock_response_content = """
        ```json
        {
            "botMessage": {
                "messageId": 5001,
                "text": "안녕하세요! 요즘 운동이나 생활 습관에서 가장 고민되는 부분이 무엇인가요?",
                "options_INVALID": []
            }
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1001,
            "userId": 12345,
            "initialContext": {
                "appGoal": "체중 감량",
                "lifestyleType": "NIGHT"
            }
        }

        response = client.post("/ai/chat/sessions", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("AI agent's response did not match the expected ChatSessionResponse schema", response.json()["detail"])

class TestChatMessageAPI(unittest.TestCase):
    @patch('api_server.run_agent_system')
    def test_handle_chat_message_text_input_success(self, mock_run_agent_system):
        mock_response_content = """
        ```json
        {
            "botMessage": {
                "messageId": 5002,
                "text": "알겠습니다. 어떤 운동이 힘든지 더 자세히 알려주시겠어요?",
                "options": []
            },
            "state": {
                "isTerminal": false
            }
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1,
            "userId": 12345, # Added userId here
            "input": {
                "type": "TEXT",
                "text": "운동이 너무 힘들어요"
            },
            "timestamp": "2026-01-11T21:10:00+09:00"
        }

        response = client.post("/ai/chat/messages", json=request_payload)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("botMessage", response_data)
        self.assertIn("state", response_data)
        self.assertEqual(response_data["botMessage"]["text"], "알겠습니다. 어떤 운동이 힘든지 더 자세히 알려주시겠어요?")
        self.assertFalse(response_data["state"]["isTerminal"])
        ChatMessageResponse(**response_data)

        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("사용자 텍스트 입력: 운동이 너무 힘들어요", kwargs["user_request"])
        self.assertIn("event", kwargs["user_payload"])
        self.assertEqual(kwargs["user_id"], "12345")


    @patch('api_server.run_agent_system')
    def test_handle_chat_message_option_input_success(self, mock_run_agent_system):
        mock_response_content = """
        ```json
        {
            "botMessage": {
                "messageId": 5003,
                "text": "시간이 부족하시군요. 어떤 시간에 운동을 주로 하시나요?",
                "options": [
                    {"label": "아침 일찍", "value": "TIME_MORNING"},
                    {"label": "점심시간", "value": "TIME_LUNCH"}
                ]
            },
            "state": {
                "isTerminal": false
            }
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1,
            "userId": 12345, # Added userId here
            "input": {
                "type": "OPTION",
                "value": "TIME_SHORTAGE"
            },
            "timestamp": "2026-01-11T21:15:00+09:00"
        }

        response = client.post("/ai/chat/messages", json=request_payload)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("botMessage", response_data)
        self.assertIn("state", response_data)
        self.assertEqual(response_data["botMessage"]["text"], "시간이 부족하시군요. 어떤 시간에 운동을 주로 하시나요?")
        self.assertFalse(response_data["state"]["isTerminal"])
        ChatMessageResponse(**response_data)

        mock_run_agent_system.assert_called_once()
        args, kwargs = mock_run_agent_system.call_args
        self.assertIn("사용자 선택지 입력: TIME_SHORTAGE", kwargs["user_request"])
        self.assertEqual(kwargs["user_id"], "12345") # user_id will be passed from the request


    @patch('api_server.run_agent_system')
    def test_handle_chat_message_ai_response_parse_error(self, mock_run_agent_system):
        mock_run_agent_system.return_value = {"agent_response": "This is not JSON", "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1,
            "userId": 12345, # Added userId here
            "input": {
                "type": "TEXT",
                "text": "운동이 너무 힘들어요"
            },
            "timestamp": "2026-01-11T21:10:00+09:00"
        }

        response = client.post("/ai/chat/messages", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to parse AI agent's response as JSON", response.json()["detail"])

    @patch('api_server.run_agent_system')
    def test_handle_chat_message_ai_response_validation_error(self, mock_run_agent_system):
        mock_response_content = """
        ```json
        {
            "botMessage": {
                "messageId": 5002,
                "text": "챗봇 응답",
                "options_INVALID": []
            },
            "state": {
                "isTerminal": "not_boolean" # Invalid type
            }
        }
        ```
        """
        mock_run_agent_system.return_value = {"agent_response": mock_response_content, "selected_agent": "coach"}

        request_payload = {
            "sessionId": 1,
            "userId": 12345, # Added userId here
            "input": {
                "type": "TEXT",
                "text": "운동이 너무 힘들어요"
            },
            "timestamp": "2026-01-11T21:10:00+09:00"
        }

        response = client.post("/ai/chat/messages", json=request_payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("AI agent's response did not match the expected ChatMessageResponse schema", response.json()["detail"])

if __name__ == '__main__':
    unittest.main()