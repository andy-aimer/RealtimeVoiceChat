"""
Unit tests for text_similarity.py and text_context.py modules.

Tests TextSimilarity comparison algorithms with different focus modes,
and TextContext window management for extracting meaningful text segments.
"""
import pytest
import sys
import os

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from text_similarity import TextSimilarity
from text_context import TextContext


# ==================== TextSimilarity Tests ====================

class TestTextSimilarityInitialization:
    """Tests for TextSimilarity initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        ts = TextSimilarity()
        
        assert ts.similarity_threshold == 0.96
        assert ts.n_words == 5
        assert ts.focus == 'weighted'
        assert ts.end_weight == 0.7
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        ts = TextSimilarity(
            similarity_threshold=0.8,
            n_words=10,
            focus='end',
            end_weight=0.5
        )
        
        assert ts.similarity_threshold == 0.8
        assert ts.n_words == 10
        assert ts.focus == 'end'
        assert ts.end_weight == 0.0  # Should be 0 for non-weighted focus
    
    def test_invalid_threshold_raises_error(self):
        """Test that invalid similarity_threshold raises ValueError."""
        with pytest.raises(ValueError, match="similarity_threshold must be between 0.0 and 1.0"):
            TextSimilarity(similarity_threshold=1.5)
        
        with pytest.raises(ValueError, match="similarity_threshold must be between 0.0 and 1.0"):
            TextSimilarity(similarity_threshold=-0.1)
    
    def test_invalid_n_words_raises_error(self):
        """Test that invalid n_words raises ValueError."""
        with pytest.raises(ValueError, match="n_words must be a positive integer"):
            TextSimilarity(n_words=0)
        
        with pytest.raises(ValueError, match="n_words must be a positive integer"):
            TextSimilarity(n_words=-5)
        
        with pytest.raises(ValueError, match="n_words must be a positive integer"):
            TextSimilarity(n_words=5.5)
    
    def test_invalid_focus_raises_error(self):
        """Test that invalid focus raises ValueError."""
        with pytest.raises(ValueError, match="focus must be 'end', 'weighted', or 'overall'"):
            TextSimilarity(focus='invalid')
    
    def test_invalid_end_weight_raises_error(self):
        """Test that invalid end_weight raises ValueError."""
        with pytest.raises(ValueError, match="end_weight must be between 0.0 and 1.0"):
            TextSimilarity(end_weight=1.5)
        
        with pytest.raises(ValueError, match="end_weight must be between 0.0 and 1.0"):
            TextSimilarity(end_weight=-0.1)


class TestTextSimilarityNormalizeText:
    """Tests for _normalize_text method."""
    
    def test_lowercase_conversion(self):
        """Test conversion to lowercase."""
        ts = TextSimilarity()
        assert ts._normalize_text("HELLO WORLD") == "hello world"
        assert ts._normalize_text("Hello World") == "hello world"
    
    def test_punctuation_removal(self):
        """Test removal of punctuation."""
        ts = TextSimilarity()
        assert ts._normalize_text("Hello, World!") == "hello world"
        assert ts._normalize_text("Test... end?") == "test end"
    
    def test_whitespace_normalization(self):
        """Test normalization of whitespace."""
        ts = TextSimilarity()
        assert ts._normalize_text("Hello    World") == "hello world"
        assert ts._normalize_text("Test\n\tEnd") == "test end"
    
    def test_empty_string(self):
        """Test normalization of empty string."""
        ts = TextSimilarity()
        assert ts._normalize_text("") == ""
        assert ts._normalize_text("   ") == ""
    
    def test_non_string_input(self):
        """Test handling of non-string input."""
        ts = TextSimilarity()
        assert ts._normalize_text(12345) == ""
        assert ts._normalize_text(None) == ""


class TestTextSimilarityGetLastNWords:
    """Tests for _get_last_n_words_text method."""
    
    def test_exact_n_words(self):
        """Test extracting exactly n words."""
        ts = TextSimilarity(n_words=3)
        text = "one two three four five"
        assert ts._get_last_n_words_text(text) == "three four five"
    
    def test_fewer_than_n_words(self):
        """Test text with fewer than n words."""
        ts = TextSimilarity(n_words=5)
        text = "one two three"
        assert ts._get_last_n_words_text(text) == "one two three"
    
    def test_single_word(self):
        """Test single word text."""
        ts = TextSimilarity(n_words=5)
        text = "hello"
        assert ts._get_last_n_words_text(text) == "hello"
    
    def test_empty_string(self):
        """Test empty string."""
        ts = TextSimilarity(n_words=5)
        text = ""
        assert ts._get_last_n_words_text(text) == ""


class TestTextSimilarityCalculateSimilarityOverall:
    """Tests for calculate_similarity with 'overall' focus."""
    
    def test_identical_texts(self):
        """Test identical texts have 1.0 similarity."""
        ts = TextSimilarity(focus='overall')
        text = "This is a test sentence."
        assert ts.calculate_similarity(text, text) == pytest.approx(1.0)
    
    def test_completely_different_texts(self):
        """Test completely different texts have low similarity."""
        ts = TextSimilarity(focus='overall')
        text1 = "Hello world"
        text2 = "Goodbye universe"
        similarity = ts.calculate_similarity(text1, text2)
        assert similarity < 0.5
    
    def test_similar_texts(self):
        """Test similar texts have high similarity."""
        ts = TextSimilarity(focus='overall')
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick brown fox jumps over a lazy dog"
        similarity = ts.calculate_similarity(text1, text2)
        assert similarity > 0.9
    
    def test_case_insensitive(self):
        """Test that comparison is case-insensitive."""
        ts = TextSimilarity(focus='overall')
        text1 = "HELLO WORLD"
        text2 = "hello world"
        assert ts.calculate_similarity(text1, text2) == pytest.approx(1.0)
    
    def test_punctuation_ignored(self):
        """Test that punctuation is ignored."""
        ts = TextSimilarity(focus='overall')
        text1 = "Hello, World!"
        text2 = "Hello World"
        assert ts.calculate_similarity(text1, text2) == pytest.approx(1.0)
    
    def test_both_empty_strings(self):
        """Test two empty strings are identical."""
        ts = TextSimilarity(focus='overall')
        assert ts.calculate_similarity("", "") == pytest.approx(1.0)
    
    def test_one_empty_string(self):
        """Test one empty string has 0.0 similarity."""
        ts = TextSimilarity(focus='overall')
        assert ts.calculate_similarity("hello", "") == pytest.approx(0.0)
        assert ts.calculate_similarity("", "hello") == pytest.approx(0.0)


class TestTextSimilarityCalculateSimilarityEnd:
    """Tests for calculate_similarity with 'end' focus."""
    
    def test_same_endings(self):
        """Test texts with same endings have high similarity."""
        ts = TextSimilarity(focus='end', n_words=3)
        text1 = "This is a very long introduction to the same three words"
        text2 = "Completely different start but the same three words"
        similarity = ts.calculate_similarity(text1, text2)
        assert similarity == pytest.approx(1.0)
    
    def test_different_endings(self):
        """Test texts with different endings have lower similarity."""
        ts = TextSimilarity(focus='end', n_words=3)
        text1 = "This is a test ending one"
        text2 = "This is a test ending two"
        similarity = ts.calculate_similarity(text1, text2)
        # Last 3 words: "test ending one" vs "test ending two" = 2/3 match ≈ 0.87
        assert similarity < 0.9  # Adjusted threshold
    
    def test_short_texts(self):
        """Test texts shorter than n_words."""
        ts = TextSimilarity(focus='end', n_words=5)
        text1 = "one two"
        text2 = "one two"
        similarity = ts.calculate_similarity(text1, text2)
        assert similarity == pytest.approx(1.0)


class TestTextSimilarityCalculateSimilarityWeighted:
    """Tests for calculate_similarity with 'weighted' focus."""
    
    def test_weighted_combines_overall_and_end(self):
        """Test weighted mode combines overall and end similarity."""
        ts = TextSimilarity(focus='weighted', n_words=3, end_weight=0.7)
        text1 = "Start middle end"
        text2 = "Different start end"
        
        # Calculate weighted similarity
        similarity_weighted = ts.calculate_similarity(text1, text2)
        
        # Calculate overall similarity
        ts_overall = TextSimilarity(focus='overall')
        similarity_overall = ts_overall.calculate_similarity(text1, text2)
        
        # Calculate end similarity
        ts_end = TextSimilarity(focus='end', n_words=3)
        similarity_end = ts_end.calculate_similarity(text1, text2)
        
        # Weighted should be between overall and end
        assert min(similarity_overall, similarity_end) <= similarity_weighted <= max(similarity_overall, similarity_end)
    
    def test_end_weight_zero(self):
        """Test weighted mode with end_weight=0 matches overall."""
        ts_weighted = TextSimilarity(focus='weighted', end_weight=0.0)
        ts_overall = TextSimilarity(focus='overall')
        
        text1 = "This is a test"
        text2 = "This is a demo"
        
        # Should be very close (not exact due to floating point)
        assert abs(ts_weighted.calculate_similarity(text1, text2) - 
                   ts_overall.calculate_similarity(text1, text2)) < 0.01


class TestTextSimilarityAreTextsSimilar:
    """Tests for are_texts_similar method."""
    
    def test_similar_texts_above_threshold(self):
        """Test texts above threshold are considered similar."""
        ts = TextSimilarity(similarity_threshold=0.9, focus='overall')
        text1 = "The quick brown fox"
        text2 = "The quick brown fox"
        assert ts.are_texts_similar(text1, text2) is True
    
    def test_dissimilar_texts_below_threshold(self):
        """Test texts below threshold are not similar."""
        ts = TextSimilarity(similarity_threshold=0.9, focus='overall')
        text1 = "Hello world"
        text2 = "Goodbye universe"
        assert ts.are_texts_similar(text1, text2) is False
    
    def test_threshold_boundary(self):
        """Test behavior at threshold boundary."""
        ts = TextSimilarity(similarity_threshold=0.95, focus='overall')
        text1 = "Test sentence"
        text2 = "Test sentence"
        
        # Identical texts should be above any threshold
        assert ts.are_texts_similar(text1, text2) is True


# ==================== TextContext Tests ====================

class TestTextContextInitialization:
    """Tests for TextContext initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default split tokens."""
        tc = TextContext()
        
        default_tokens = {".", "!", "?", ",", ";", ":", "\n", "-", "。", "、"}
        assert tc.split_tokens == default_tokens
    
    def test_custom_split_tokens(self):
        """Test initialization with custom split tokens."""
        custom_tokens = {".", "!", "?"}
        tc = TextContext(split_tokens=custom_tokens)
        
        assert tc.split_tokens == custom_tokens
    
    def test_split_tokens_converted_to_set(self):
        """Test that split_tokens is converted to set."""
        tc = TextContext(split_tokens=[".", "!", "."])  # Duplicate "."
        
        assert isinstance(tc.split_tokens, set)
        assert len(tc.split_tokens) == 2  # Only unique tokens


class TestTextContextGetContext:
    """Tests for get_context method."""
    
    def test_simple_sentence_extraction(self):
        """Test extracting a simple sentence."""
        tc = TextContext()
        text = "This is a test sentence. More text here."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context == "This is a test sentence."
        assert remaining == " More text here."
    
    def test_min_length_requirement(self):
        """Test that context must meet minimum length."""
        tc = TextContext()
        text = "Hi. This is a longer sentence."
        
        # "Hi." is too short (min_len=6)
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=5)
        
        # Should find "Hi. This is a longer sentence."
        assert context is not None
        assert len(context) >= 6
    
    def test_min_alnum_count_requirement(self):
        """Test that context must have minimum alphanumeric characters."""
        tc = TextContext()
        text = "...!!! This has enough alphanumeric characters."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        # Should skip "...!!!" and find the full sentence
        assert context is not None
        alnum_count = sum(c.isalnum() for c in context)
        assert alnum_count >= 10
    
    def test_max_length_constraint(self):
        """Test that search stops at max_len."""
        tc = TextContext()
        text = "A" * 200 + "."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=50, min_alnum_count=10)
        
        # Should not find context since "." is beyond max_len
        assert context is None
        assert remaining is None
    
    def test_no_split_token_found(self):
        """Test when no split token is found."""
        tc = TextContext()
        text = "No split tokens here"
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context is None
        assert remaining is None
    
    def test_multiple_split_tokens(self):
        """Test finding first suitable split token."""
        tc = TextContext()
        text = "First, second! Third? Fourth."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=3)
        
        # Should find "First,"
        assert context == "First,"
        assert remaining == " second! Third? Fourth."
    
    def test_question_mark_split(self):
        """Test splitting on question mark."""
        tc = TextContext()
        text = "Is this working? Yes it is."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context == "Is this working?"
        assert remaining == " Yes it is."
    
    def test_exclamation_split(self):
        """Test splitting on exclamation mark."""
        tc = TextContext()
        text = "This is amazing! Indeed it is."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context == "This is amazing!"
        assert remaining == " Indeed it is."
    
    def test_newline_split(self):
        """Test splitting on newline."""
        tc = TextContext()
        text = "First line with enough characters\nSecond line"
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context == "First line with enough characters\n"
        assert remaining == "Second line"
    
    def test_empty_string(self):
        """Test with empty string."""
        tc = TextContext()
        context, remaining = tc.get_context("", min_len=6, max_len=120, min_alnum_count=10)
        
        assert context is None
        assert remaining is None
    
    def test_only_punctuation(self):
        """Test string with only punctuation."""
        tc = TextContext()
        text = "...!!!???"
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        # Should not find valid context (no alphanumeric chars)
        assert context is None
        assert remaining is None


class TestTextContextEdgeCases:
    """Tests for edge cases in TextContext."""
    
    def test_exact_min_length(self):
        """Test context with exactly min_len."""
        tc = TextContext()
        text = "Exact."  # 6 characters including "."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=5)
        
        assert context == "Exact."
        assert remaining == ""
    
    def test_exact_max_length(self):
        """Test context at exactly max_len."""
        tc = TextContext()
        text = "A" * 19 + "."  # 20 characters total
        
        context, remaining = tc.get_context(text, min_len=6, max_len=20, min_alnum_count=10)
        
        assert context == "A" * 19 + "."
        assert remaining == ""
    
    def test_exact_min_alnum_count(self):
        """Test context with exactly min_alnum_count."""
        tc = TextContext()
        text = "1234567890."  # Exactly 10 alphanumeric characters
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        assert context == "1234567890."
        assert remaining == ""
    
    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        tc = TextContext()
        text = "Hello 世界! More text."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=5)
        
        assert "!" in context
        assert remaining is not None
    
    def test_very_long_text(self):
        """Test with very long text beyond max_len."""
        tc = TextContext()
        text = "A" * 1000 + ". End"
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=10)
        
        # Should not find context since "." is at position 1001
        assert context is None
        assert remaining is None
    
    def test_multiple_consecutive_split_tokens(self):
        """Test multiple consecutive split tokens."""
        tc = TextContext()
        text = "Test...!!! More text."
        
        context, remaining = tc.get_context(text, min_len=6, max_len=120, min_alnum_count=4)
        
        # Should find context at first split token that meets criteria
        assert context is not None
        assert "Test" in context


# ==================== Integration Tests ====================

class TestTextUtilsIntegration:
    """Integration tests for TextSimilarity and TextContext together."""
    
    def test_similarity_with_context_extraction(self):
        """Test using TextContext and TextSimilarity together."""
        tc = TextContext()
        ts = TextSimilarity(similarity_threshold=0.9)
        
        text1 = "This is a test sentence. More text here."
        text2 = "This is a test sentence. Different text here."
        
        # Extract contexts
        context1, _ = tc.get_context(text1, min_len=6, max_len=120, min_alnum_count=10)
        context2, _ = tc.get_context(text2, min_len=6, max_len=120, min_alnum_count=10)
        
        # Compare contexts
        assert ts.are_texts_similar(context1, context2) is True
    
    def test_different_contexts_low_similarity(self):
        """Test that different contexts have low similarity."""
        tc = TextContext()
        ts = TextSimilarity(similarity_threshold=0.9)
        
        text1 = "First sentence. More text."
        text2 = "Different sentence. Other text."
        
        context1, _ = tc.get_context(text1, min_len=6, max_len=120, min_alnum_count=10)
        context2, _ = tc.get_context(text2, min_len=6, max_len=120, min_alnum_count=10)
        
        assert ts.are_texts_similar(context1, context2) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
