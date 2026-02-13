"""
Integration test configuration.

Uses root conftest's client fixture which overrides get_db with test db_session
so the app sees fixture data (sample_user, sample_question, etc.) in the same
transaction during HTTP requests.
"""
