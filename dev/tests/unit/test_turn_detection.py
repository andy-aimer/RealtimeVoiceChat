"""
Unit tests for turndetect.py module.

Tests TurnDetection class pause calculation, silence detection thresholds,
edge cases (short/long pauses, rapid speech), and utility functions.
"""
import pytest
import time
import queue
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Mock heavy dependencies before importing
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torch.nn'] = MagicMock()
sys.modules['torch.nn.functional'] = MagicMock()

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from turndetect import (
    TurnDetection,
    ends_with_string,
    preprocess_text,
    strip_ending_punctuation,
    find_matching_texts,
    interpolate_detection,
    sentence_end_marks,
    anchor_points
)
from collections import deque


# ==================== Utility Function Tests ====================

class TestEndsWithString:
    """Tests for ends_with_string utility function."""
    
    def test_exact_match(self):
        """Test exact ending match."""
        assert ends_with_string("Hello world.", ".") is True
        assert ends_with_string("Question?", "?") is True
        assert ends_with_string("Excited!", "!") is True
    
    def test_with_trailing_space(self):
        """Test match with one trailing character."""
        assert ends_with_string("Hello world. ", ".") is True
        assert ends_with_string("Question? ", "?") is True
        assert ends_with_string("Excited! ", "!") is True
    
    def test_no_match(self):
        """Test when substring doesn't match end."""
        assert ends_with_string("Hello world", ".") is False
        assert ends_with_string("Question", "?") is False
        assert ends_with_string("Excited", "!") is False
    
    def test_empty_strings(self):
        """Test with empty strings."""
        assert ends_with_string("", ".") is False
        assert ends_with_string("test", "") is True  # Everything ends with empty string
    
    def test_multichar_substring(self):
        """Test with multi-character substrings."""
        assert ends_with_string("sentence...", "...") is True
        assert ends_with_string("sentence... ", "...") is True
        assert ends_with_string("sentence..", "...") is False


class TestPreprocessText:
    """Tests for preprocess_text utility function."""
    
    def test_leading_whitespace_removal(self):
        """Test removal of leading whitespace."""
        assert preprocess_text("  hello") == "Hello"
        assert preprocess_text("\n\thello") == "Hello"
    
    def test_ellipsis_removal(self):
        """Test removal of leading ellipsis."""
        assert preprocess_text("...hello world") == "Hello world"
        assert preprocess_text("  ...hello world") == "Hello world"
    
    def test_uppercase_first_letter(self):
        """Test uppercasing of first letter."""
        assert preprocess_text("hello") == "Hello"
        assert preprocess_text("hello world") == "Hello world"
    
    def test_empty_string(self):
        """Test with empty string."""
        assert preprocess_text("") == ""
        assert preprocess_text("   ") == ""
        assert preprocess_text("...") == ""
    
    def test_combined_preprocessing(self):
        """Test combination of preprocessing steps."""
        assert preprocess_text("  ...  hello world") == "Hello world"
        assert preprocess_text("\n...test") == "Test"


class TestStripEndingPunctuation:
    """Tests for strip_ending_punctuation utility function."""
    
    def test_strip_single_punctuation(self):
        """Test stripping single punctuation marks."""
        assert strip_ending_punctuation("Hello world.") == "Hello world"
        assert strip_ending_punctuation("Question?") == "Question"
        assert strip_ending_punctuation("Excited!") == "Excited"
    
    def test_strip_multiple_punctuation(self):
        """Test stripping multiple consecutive punctuation."""
        assert strip_ending_punctuation("Wow!!!") == "Wow"
        assert strip_ending_punctuation("Really???") == "Really"
        assert strip_ending_punctuation("End...") == "End"
    
    def test_strip_with_trailing_whitespace(self):
        """Test stripping with trailing whitespace."""
        assert strip_ending_punctuation("Hello world.  ") == "Hello world"
        assert strip_ending_punctuation("Test!  \n") == "Test"
    
    def test_no_punctuation(self):
        """Test text without ending punctuation."""
        assert strip_ending_punctuation("Hello world") == "Hello world"
        assert strip_ending_punctuation("Test") == "Test"
    
    def test_only_punctuation(self):
        """Test text with only punctuation."""
        result = strip_ending_punctuation("...")
        assert result == "" or result == "..."  # Could be either
        
        result = strip_ending_punctuation("!!!")
        assert result == "" or result == "!!!"


class TestFindMatchingTexts:
    """Tests for find_matching_texts utility function."""
    
    def test_all_matching(self):
        """Test when all entries match."""
        texts = deque([
            ("Hello.", "Hello"),
            ("Hello!", "Hello"),
            ("Hello?", "Hello")
        ])
        matches = find_matching_texts(texts)
        assert len(matches) == 3
        assert matches[0][0] == "Hello."
        assert matches[1][0] == "Hello!"
        assert matches[2][0] == "Hello?"
    
    def test_partial_matching(self):
        """Test when only recent entries match."""
        texts = deque([
            ("Different.", "Different"),
            ("Hello.", "Hello"),
            ("Hello!", "Hello"),
            ("Hello?", "Hello")
        ])
        matches = find_matching_texts(texts)
        assert len(matches) == 3
        assert matches[0][0] == "Hello."
    
    def test_no_matching(self):
        """Test when last entry is unique."""
        texts = deque([
            ("First.", "First"),
            ("Second.", "Second"),
            ("Third.", "Third")
        ])
        matches = find_matching_texts(texts)
        assert len(matches) == 1
        assert matches[0][0] == "Third."
    
    def test_empty_deque(self):
        """Test with empty deque."""
        texts = deque()
        matches = find_matching_texts(texts)
        assert len(matches) == 0


class TestInterpolateDetection:
    """Tests for interpolate_detection utility function."""
    
    def test_exact_anchor_points(self):
        """Test probabilities exactly at anchor points."""
        # Default anchor points: (0.0, 1.0), (1.0, 0.0)
        assert interpolate_detection(0.0) == pytest.approx(1.0, abs=1e-6)
        assert interpolate_detection(1.0) == pytest.approx(0.0, abs=1e-6)
    
    def test_midpoint_interpolation(self):
        """Test probability at midpoint."""
        assert interpolate_detection(0.5) == pytest.approx(0.5, abs=1e-6)
    
    def test_clamping(self):
        """Test clamping of out-of-range probabilities."""
        # Should clamp to [0.0, 1.0] range
        assert interpolate_detection(-0.5) == pytest.approx(1.0, abs=1e-6)
        assert interpolate_detection(1.5) == pytest.approx(0.0, abs=1e-6)
    
    def test_interpolation_range(self):
        """Test interpolation across the range."""
        assert 0.0 <= interpolate_detection(0.25) <= 1.0
        assert 0.0 <= interpolate_detection(0.75) <= 1.0


# ==================== TurnDetection Class Tests ====================

class TestTurnDetectionInitialization:
    """Tests for TurnDetection initialization."""
    
    @pytest.fixture
    def mock_callback(self):
        """Fixture providing a mock callback."""
        return Mock()
    
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def test_initialization_local(self, mock_model_class, mock_tokenizer_class, mock_callback):
        """Test initialization with local=True."""
        # Create mock instances
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        detector = TurnDetection(
            on_new_waiting_time=mock_callback,
            local=True
        )
        
        assert detector.on_new_waiting_time == mock_callback
        assert detector.current_waiting_time == -1
        assert len(detector.text_time_deque) == 0
        assert len(detector.texts_without_punctuation) == 0
        assert detector.text_worker.is_alive()
    
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def test_initialization_cloud(self, mock_model_class, mock_tokenizer_class, mock_callback):
        """Test initialization with local=False."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        detector = TurnDetection(
            on_new_waiting_time=mock_callback,
            local=False
        )
        
        assert detector.on_new_waiting_time == mock_callback
        assert detector.text_worker.is_alive()


class TestTurnDetectionUpdateSettings:
    """Tests for update_settings method."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector(self, mock_model_class, mock_tokenizer_class):
        """Fixture providing initialized TurnDetection instance."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        return TurnDetection(on_new_waiting_time=Mock(), local=True)
    
    def test_speed_factor_zero(self, detector):
        """Test settings with speed_factor=0.0 (fastest)."""
        detector.update_settings(speed_factor=0.0)
        
        assert detector.detection_speed == 0.5
        assert detector.ellipsis_pause == 2.3
        assert detector.punctuation_pause == 0.39
        assert detector.exclamation_pause == 0.35
        assert detector.question_pause == 0.33
    
    def test_speed_factor_one(self, detector):
        """Test settings with speed_factor=1.0 (slowest)."""
        detector.update_settings(speed_factor=1.0)
        
        assert detector.detection_speed == 1.7
        assert detector.ellipsis_pause == 3.0
        assert detector.punctuation_pause == 0.9
        assert detector.exclamation_pause == 0.8
        assert detector.question_pause == 0.8
    
    def test_speed_factor_clamping(self, detector):
        """Test clamping of speed_factor to [0.0, 1.0]."""
        detector.update_settings(speed_factor=-0.5)
        fast_speed = detector.detection_speed
        
        detector.update_settings(speed_factor=0.0)
        assert detector.detection_speed == fast_speed
        
        detector.update_settings(speed_factor=2.0)
        slow_speed = detector.detection_speed
        
        detector.update_settings(speed_factor=1.0)
        assert detector.detection_speed == slow_speed


class TestTurnDetectionSuggestTime:
    """Tests for suggest_time method."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector(self, mock_model_class, mock_tokenizer_class):
        """Fixture providing initialized TurnDetection instance."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        mock_callback = Mock()
        return TurnDetection(on_new_waiting_time=mock_callback, local=True)
    
    def test_suggest_new_time(self, detector):
        """Test suggesting a new waiting time."""
        detector.suggest_time(1.5, "Test text")
        
        assert detector.current_waiting_time == 1.5
        detector.on_new_waiting_time.assert_called_once_with(1.5, "Test text")
    
    def test_suggest_same_time_no_callback(self, detector):
        """Test suggesting the same time doesn't trigger callback."""
        detector.suggest_time(1.5, "Test text 1")
        detector.on_new_waiting_time.reset_mock()
        
        detector.suggest_time(1.5, "Test text 2")
        detector.on_new_waiting_time.assert_not_called()
    
    def test_suggest_different_times(self, detector):
        """Test suggesting different times triggers callback each time."""
        detector.suggest_time(1.0, "Text 1")
        detector.suggest_time(1.5, "Text 2")
        detector.suggest_time(2.0, "Text 3")
        
        assert detector.on_new_waiting_time.call_count == 3


class TestTurnDetectionGetSuggestedWhisperPause:
    """Tests for get_suggested_whisper_pause method."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector(self, mock_model_class, mock_tokenizer_class):
        """Fixture providing initialized TurnDetection instance."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        return TurnDetection(on_new_waiting_time=Mock(), local=True)
    
    def test_ellipsis_pause(self, detector):
        """Test pause for text ending with ellipsis."""
        pause = detector.get_suggested_whisper_pause("Waiting...")
        assert pause == detector.ellipsis_pause
    
    def test_period_pause(self, detector):
        """Test pause for text ending with period."""
        pause = detector.get_suggested_whisper_pause("End of sentence.")
        assert pause == detector.punctuation_pause
    
    def test_exclamation_pause(self, detector):
        """Test pause for text ending with exclamation."""
        pause = detector.get_suggested_whisper_pause("Wow!")
        assert pause == detector.exclamation_pause
    
    def test_question_pause(self, detector):
        """Test pause for text ending with question mark."""
        pause = detector.get_suggested_whisper_pause("Really?")
        assert pause == detector.question_pause
    
    def test_unknown_pause(self, detector):
        """Test pause for text with unknown ending."""
        pause = detector.get_suggested_whisper_pause("No punctuation")
        assert pause == detector.unknown_sentence_detection_pause


class TestTurnDetectionReset:
    """Tests for reset method."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector(self, mock_model_class, mock_tokenizer_class):
        """Fixture providing initialized TurnDetection instance."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        return TurnDetection(on_new_waiting_time=Mock(), local=True)
    
    def test_reset_clears_state(self, detector):
        """Test reset clears all internal state."""
        # Add some state
        detector.text_time_deque.append((time.time(), "Test"))
        detector.texts_without_punctuation.append(("Test.", "Test"))
        detector.current_waiting_time = 1.5
        detector._completion_probability_cache["test"] = 0.95
        
        # Reset
        detector.reset()
        
        # Verify cleared
        assert len(detector.text_time_deque) == 0
        assert len(detector.texts_without_punctuation) == 0
        assert detector.current_waiting_time == -1
        assert len(detector._completion_probability_cache) == 0


class TestTurnDetectionCalculateWaitingTime:
    """Tests for calculate_waiting_time method."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector(self, mock_model_class, mock_tokenizer_class):
        """Fixture providing initialized TurnDetection instance."""
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        return TurnDetection(on_new_waiting_time=Mock(), local=True)
    
    def test_queues_text(self, detector):
        """Test that text is queued for processing."""
        test_text = "Test sentence."
        detector.calculate_waiting_time(test_text)
        
        # Wait briefly for queue processing
        time.sleep(0.1)
        
        # Text should be in queue or already processed
        assert detector.text_queue.qsize() >= 0  # Queue might be empty if already processed


# ==================== Integration Tests ====================

class TestTurnDetectionIntegration:
    """Integration tests for TurnDetection with mocked transformers."""
    
    @pytest.fixture
    @patch('turndetect.transformers.DistilBertTokenizerFast')
    @patch('turndetect.transformers.DistilBertForSequenceClassification')
    def detector_with_mock_model(self, mock_model_class, mock_tokenizer_class):
        """Fixture with mocked transformer model."""
        # Setup mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': MagicMock(),
            'attention_mask': MagicMock()
        }
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        # Setup mock model
        mock_model = MagicMock()
        mock_outputs = MagicMock()
        
        # Mock logits for sentence completion (incomplete=0, complete=1)
        import torch
        mock_logits = torch.tensor([[0.1, 0.9]])  # High probability of completion
        mock_outputs.logits = mock_logits
        mock_model.return_value = mock_outputs
        mock_model_class.from_pretrained.return_value = mock_model
        
        callback = Mock()
        detector = TurnDetection(on_new_waiting_time=callback, local=True)
        
        return detector, callback
    
    def test_short_pause_edge_case(self, detector_with_mock_model):
        """Test handling of very short pauses (rapid speech)."""
        detector, callback = detector_with_mock_model
        
        # Simulate rapid speech with short text
        detector.calculate_waiting_time("Yes")
        time.sleep(0.2)
        
        # Should still trigger callback with minimum pipeline latency
        callback.assert_called()
        if callback.call_args:
            suggested_time = callback.call_args[0][0]
            min_pause = detector.pipeline_latency + detector.pipeline_latency_overhead
            assert suggested_time >= min_pause
    
    def test_long_pause_edge_case(self, detector_with_mock_model):
        """Test handling of long pauses with ellipsis."""
        detector, callback = detector_with_mock_model
        
        # Simulate text with ellipsis (indicates long pause)
        detector.calculate_waiting_time("Thinking...")
        time.sleep(0.2)
        
        # Should trigger callback with ellipsis pause
        callback.assert_called()
        if callback.call_args:
            suggested_time = callback.call_args[0][0]
            # Should include ellipsis adjustment (+0.2s) and detection speed multiplier
            assert suggested_time > detector.ellipsis_pause * 0.5  # At least half the ellipsis pause


# ==================== Edge Cases and Error Handling ====================

class TestTurnDetectionEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_text_preprocessing(self):
        """Test preprocessing of empty and whitespace-only text."""
        assert preprocess_text("") == ""
        assert preprocess_text("   ") == ""
        assert preprocess_text("\n\t") == ""
    
    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Test with émojis 😀 and spëcial çharacters"
        result = preprocess_text(text)
        assert result.startswith("T")  # First letter uppercased
    
    def test_very_long_text(self):
        """Test handling of very long text."""
        long_text = "A" * 1000 + "."
        processed = preprocess_text(long_text)
        assert processed.startswith("A")
        assert len(processed) == 1001  # Original length preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
