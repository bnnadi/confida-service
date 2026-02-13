"""
Unit tests for TTS configuration validation.

Tests the TTS configuration settings and validation logic including:
- TTS provider validation
- Vendor API key validation
- Numeric setting validation
- Format validation
- Startup validation
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from app.config import Settings
from app.utils.validation import ValidationService
from app.startup import validate_startup


class TestTTSConfigurationSettings:
    """Tests for TTS configuration settings in Settings class."""
    
    @pytest.mark.unit
    def test_default_tts_settings(self):
        """Test default TTS settings are correct."""
        settings = Settings()
        
        assert settings.TTS_PROVIDER == "coqui"
        assert settings.TTS_FALLBACK_PROVIDER == ""
        assert settings.TTS_VOICE_VERSION == 1
        assert settings.TTS_DEFAULT_VOICE_ID == "confida-default-en"
        assert settings.TTS_DEFAULT_FORMAT == "mp3"
        assert settings.TTS_CACHE_TTL == 604800  # 7 days
        assert settings.TTS_TIMEOUT == 30
        assert settings.TTS_RETRY_ATTEMPTS == 3
        assert settings.TTS_MAX_CONCURRENT == 5
    
    @pytest.mark.unit
    def test_tts_settings_from_env(self):
        """Test TTS settings can be overridden from environment variables.
        
        Since Settings is a plain class with os.getenv() calls resolved at class
        definition time, we must reload the module to re-evaluate the class body
        with the patched environment.
        """
        import importlib
        import app.config
        
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "elevenlabs",
            "TTS_FALLBACK_PROVIDER": "coqui",
            "TTS_VOICE_VERSION": "2",
            "TTS_DEFAULT_VOICE_ID": "test-voice",
            "TTS_DEFAULT_FORMAT": "wav",
            "TTS_CACHE_TTL": "3600",
            "TTS_TIMEOUT": "60",
            "TTS_RETRY_ATTEMPTS": "5",
            "TTS_MAX_CONCURRENT": "10",
            "ELEVENLABS_API_KEY": "test-key-12345678901234567890",
            "PLAYHT_API_KEY": "playht-key-12345678901234567890",
            "PLAYHT_USER_ID": "user-123"
        }):
            # Reload the config module to re-evaluate class-level os.getenv() calls
            importlib.reload(app.config)
            from app.config import get_settings
            get_settings.cache_clear()
            
            ReloadedSettings = app.config.Settings
            settings = ReloadedSettings()
            
            assert settings.TTS_PROVIDER == "elevenlabs"
            assert settings.TTS_FALLBACK_PROVIDER == "coqui"
            assert settings.TTS_VOICE_VERSION == 2
            assert settings.TTS_DEFAULT_VOICE_ID == "test-voice"
            assert settings.TTS_DEFAULT_FORMAT == "wav"
            assert settings.TTS_CACHE_TTL == 3600
            assert settings.TTS_TIMEOUT == 60
            assert settings.TTS_RETRY_ATTEMPTS == 5
            assert settings.TTS_MAX_CONCURRENT == 10
            assert settings.ELEVENLABS_API_KEY == "test-key-12345678901234567890"
            assert settings.PLAYHT_API_KEY == "playht-key-12345678901234567890"
            assert settings.PLAYHT_USER_ID == "user-123"
        
        # Restore original module state
        importlib.reload(app.config)
        app.config.get_settings.cache_clear()


class TestTTSConfigurationValidation:
    """Tests for TTS configuration validation."""
    
    @pytest.mark.unit
    def test_valid_coqui_configuration(self):
        """Test validation passes for valid coqui configuration."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "coqui",
            "TTS_DEFAULT_FORMAT": "mp3"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have no TTS-related errors
            tts_errors = [e for e in errors if "TTS" in e or "ELEVENLABS" in e or "PLAYHT" in e]
            assert len(tts_errors) == 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_invalid_tts_provider(self):
        """Test validation fails for invalid TTS provider."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "invalid_provider"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about invalid provider
            tts_errors = [e for e in errors if "TTS_PROVIDER" in e and "invalid_provider" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_elevenlabs_missing_api_key(self):
        """Test validation fails when ElevenLabs provider selected but API key missing."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "elevenlabs",
            "ELEVENLABS_API_KEY": ""
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about missing API key
            tts_errors = [e for e in errors if "ELEVENLABS_API_KEY" in e and "required" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_elevenlabs_with_api_key(self):
        """Test validation passes when ElevenLabs provider selected with valid API key."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "elevenlabs",
            "ELEVENLABS_API_KEY": "valid-key-12345678901234567890"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have no errors about missing API key
            tts_errors = [e for e in errors if "ELEVENLABS_API_KEY" in e and "required" in e]
            assert len(tts_errors) == 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_playht_missing_credentials(self):
        """Test validation fails when PlayHT provider selected but credentials missing."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "playht",
            "PLAYHT_API_KEY": "",
            "PLAYHT_USER_ID": ""
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have errors about missing credentials
            tts_errors = [e for e in errors if ("PLAYHT_API_KEY" in e or "PLAYHT_USER_ID" in e) and "required" in e]
            assert len(tts_errors) >= 2  # Both API key and user ID should be required
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_playht_with_credentials(self):
        """Test validation passes when PlayHT provider selected with valid credentials."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "playht",
            "PLAYHT_API_KEY": "valid-key-12345678901234567890",
            "PLAYHT_USER_ID": "user-123"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have no errors about missing credentials
            tts_errors = [e for e in errors if ("PLAYHT_API_KEY" in e or "PLAYHT_USER_ID" in e) and "required" in e]
            assert len(tts_errors) == 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_invalid_tts_format(self):
        """Test validation fails for invalid TTS format."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_DEFAULT_FORMAT": "invalid_format"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about invalid format
            tts_errors = [e for e in errors if "TTS_DEFAULT_FORMAT" in e and "invalid_format" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_invalid_tts_voice_version(self):
        """Test validation fails for invalid voice version."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_VOICE_VERSION": "0"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about invalid voice version
            tts_errors = [e for e in errors if "TTS_VOICE_VERSION" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_invalid_tts_timeout(self):
        """Test validation fails for invalid timeout."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_TIMEOUT": "0"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about invalid timeout
            tts_errors = [e for e in errors if "TTS_TIMEOUT" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_invalid_tts_cache_ttl(self):
        """Test validation fails for invalid cache TTL."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_CACHE_TTL": "-1"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have error about invalid cache TTL
            tts_errors = [e for e in errors if "TTS_CACHE_TTL" in e]
            assert len(tts_errors) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_high_cache_ttl_warning(self):
        """Test validation warns for very high cache TTL."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_CACHE_TTL": "2592001"  # > 30 days
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have warning about high cache TTL
            tts_warnings = [w for w in warnings if "TTS_CACHE_TTL" in w]
            assert len(tts_warnings) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_unused_vendor_key_warning(self):
        """Test validation warns when vendor key is set but provider not used."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "coqui",
            "ELEVENLABS_API_KEY": "some-key-12345678901234567890"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have warning about unused API key
            tts_warnings = [w for w in warnings if "ELEVENLABS_API_KEY" in w and "not 'elevenlabs'" in w]
            assert len(tts_warnings) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_same_fallback_provider_warning(self):
        """Test validation warns when fallback provider is same as main provider."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "coqui",
            "TTS_FALLBACK_PROVIDER": "coqui"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have warning about same provider
            tts_warnings = [w for w in warnings if "TTS_FALLBACK_PROVIDER" in w and "same" in w]
            assert len(tts_warnings) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_short_api_key_warning(self):
        """Test validation warns for short API keys."""
        import importlib
        import app.config
        import app.utils.validation
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "elevenlabs",
            "ELEVENLABS_API_KEY": "short"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            app.config.get_settings.cache_clear()
            
            from app.utils.validation import ValidationService
            validator = ValidationService()
            errors, warnings = validator.validate_configuration()
            
            # Should have warning about short API key
            tts_warnings = [w for w in warnings if "ELEVENLABS_API_KEY" in w and "short" in w]
            assert len(tts_warnings) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        app.config.get_settings.cache_clear()


class TestTTSStartupValidation:
    """Tests for TTS configuration validation at startup."""
    
    @pytest.mark.unit
    def test_startup_validation_with_valid_config(self):
        """Test startup validation passes with valid TTS config."""
        import importlib
        import app.config
        import app.startup
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "coqui"
        }):
            importlib.reload(app.config)
            importlib.reload(app.startup)
            app.config.get_settings.cache_clear()
            
            with patch('app.startup.get_ai_client', return_value=MagicMock()):
                with patch('app.startup.logger') as mock_logger:
                    from app.startup import validate_startup
                    validate_startup()
                    
                    # Should log success
                    info_calls = [call for call in mock_logger.info.call_args_list 
                                if any("✅" in str(arg) for arg in call[0])]
                    assert len(info_calls) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.startup)
        app.config.get_settings.cache_clear()
    
    @pytest.mark.unit
    def test_startup_validation_with_invalid_config(self):
        """Test startup validation logs errors with invalid TTS config."""
        import importlib
        import app.config
        import app.utils.validation
        import app.utils.config_validator
        import app.startup
        with patch.dict(os.environ, {
            "TTS_PROVIDER": "invalid_provider"
        }):
            importlib.reload(app.config)
            importlib.reload(app.utils.validation)
            importlib.reload(app.utils.config_validator)
            importlib.reload(app.startup)
            app.config.get_settings.cache_clear()
            
            with patch('app.startup.get_ai_client', return_value=MagicMock()):
                with patch('app.startup.logger') as mock_logger:
                    from app.startup import validate_startup
                    validate_startup()
                    
                    # Should log error
                    error_calls = [call for call in mock_logger.error.call_args_list 
                                  if any("Configuration errors" in str(arg) for arg in call[0])]
                    assert len(error_calls) > 0
        
        importlib.reload(app.config)
        importlib.reload(app.utils.validation)
        importlib.reload(app.utils.config_validator)
        importlib.reload(app.startup)
        app.config.get_settings.cache_clear()

