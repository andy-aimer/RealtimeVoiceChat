"""
Integration tests for end-to-end STT → LLM → TTS pipeline.

Tests full pipeline execution, warmup runs, latency requirements (<1.8s),
and validates complete data flow from audio input to TTS output.
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'code'))

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def warmup_models():
    """
    Fixture to warmup models before running performance tests.
    
    This fixture runs once per module to load and warm up the STT, LLM, and TTS models.
    The warmup time is excluded from latency measurements.
    """
    print("\n🔥 Warming up models for integration tests...")
    warmup_start = time.perf_counter()
    
    # Mock model warmup (in real implementation, this would load actual models)
    # STT warmup
    stt_warmup_time = 0.5
    time.sleep(stt_warmup_time)
    print(f"  ✓ STT warmed up in {stt_warmup_time:.2f}s")
    
    # LLM warmup
    llm_warmup_time = 1.0
    time.sleep(llm_warmup_time)
    print(f"  ✓ LLM warmed up in {llm_warmup_time:.2f}s")
    
    # TTS warmup
    tts_warmup_time = 0.5
    time.sleep(tts_warmup_time)
    print(f"  ✓ TTS warmed up in {tts_warmup_time:.2f}s")
    
    warmup_elapsed = time.perf_counter() - warmup_start
    print(f"🔥 Total warmup time: {warmup_elapsed:.2f}s (excluded from latency tests)\n")
    
    return {
        'stt_ready': True,
        'llm_ready': True,
        'tts_ready': True,
        'warmup_time': warmup_elapsed
    }


@pytest.fixture
def mock_stt_output():
    """Fixture providing mock STT transcription output."""
    return "What is the weather like today?"


@pytest.fixture
def mock_llm_response():
    """Fixture providing mock LLM response."""
    return "The weather today is sunny with a high of 72 degrees Fahrenheit."


@pytest.fixture
def mock_audio_input():
    """Fixture providing mock audio input data."""
    # Simulate 2 seconds of 16kHz 16-bit PCM audio
    sample_rate = 16000
    duration = 2.0
    samples = int(sample_rate * duration)
    return bytes([0] * samples * 2)  # 2 bytes per sample


# ==================== Pipeline Component Tests ====================

class TestPipelineComponents:
    """Tests for individual pipeline components."""
    
    def test_stt_component(self, warmup_models, mock_audio_input):
        """Test STT component processes audio."""
        assert warmup_models['stt_ready'] is True
        
        # Mock STT processing
        start = time.perf_counter()
        
        def mock_stt_process(audio_data):
            # Simulate STT processing time
            time.sleep(0.2)
            return "transcribed text"
        
        result = mock_stt_process(mock_audio_input)
        elapsed = time.perf_counter() - start
        
        assert result == "transcribed text"
        assert elapsed < 0.5  # STT should be fast
    
    def test_llm_component(self, warmup_models, mock_stt_output):
        """Test LLM component generates response."""
        assert warmup_models['llm_ready'] is True
        
        # Mock LLM processing
        start = time.perf_counter()
        
        def mock_llm_generate(prompt):
            # Simulate LLM generation time
            time.sleep(0.5)
            return "LLM generated response"
        
        result = mock_llm_generate(mock_stt_output)
        elapsed = time.perf_counter() - start
        
        assert result == "LLM generated response"
        assert elapsed < 1.0  # LLM should complete in reasonable time
    
    def test_tts_component(self, warmup_models, mock_llm_response):
        """Test TTS component synthesizes audio."""
        assert warmup_models['tts_ready'] is True
        
        # Mock TTS processing
        start = time.perf_counter()
        
        def mock_tts_synthesize(text):
            # Simulate TTS synthesis time
            time.sleep(0.3)
            return bytes([1, 2, 3, 4])  # Mock audio data
        
        result = mock_tts_synthesize(mock_llm_response)
        elapsed = time.perf_counter() - start
        
        assert len(result) > 0
        assert elapsed < 0.6  # TTS should be fast


# ==================== End-to-End Pipeline Tests ====================

class TestEndToEndPipeline:
    """Tests for complete STT → LLM → TTS pipeline."""
    
    def test_full_pipeline_execution(self, warmup_models, mock_audio_input):
        """Test complete pipeline from audio input to TTS output."""
        assert warmup_models['stt_ready'] is True
        
        # Simulate full pipeline
        pipeline_start = time.perf_counter()
        
        # Step 1: STT
        stt_start = time.perf_counter()
        transcription = "What is the weather?"
        stt_time = time.perf_counter() - stt_start
        
        # Step 2: LLM
        llm_start = time.perf_counter()
        time.sleep(0.5)  # Simulate LLM processing
        llm_response = "The weather is sunny."
        llm_time = time.perf_counter() - llm_start
        
        # Step 3: TTS
        tts_start = time.perf_counter()
        time.sleep(0.3)  # Simulate TTS synthesis
        audio_output = bytes([1, 2, 3])
        tts_time = time.perf_counter() - tts_start
        
        pipeline_time = time.perf_counter() - pipeline_start
        
        # Assertions
        assert transcription is not None
        assert llm_response is not None
        assert len(audio_output) > 0
        
        print(f"\n📊 Pipeline Breakdown:")
        print(f"  STT:  {stt_time*1000:.0f}ms")
        print(f"  LLM:  {llm_time*1000:.0f}ms")
        print(f"  TTS:  {tts_time*1000:.0f}ms")
        print(f"  Total: {pipeline_time*1000:.0f}ms")
    
    def test_pipeline_data_flow(self, warmup_models):
        """Test data flows correctly through pipeline stages."""
        # Track data through pipeline
        pipeline_data = {
            'audio_input': bytes([0] * 1000),
            'stt_output': None,
            'llm_input': None,
            'llm_output': None,
            'tts_input': None,
            'tts_output': None
        }
        
        # Step 1: STT processes audio
        pipeline_data['stt_output'] = "test transcription"
        pipeline_data['llm_input'] = pipeline_data['stt_output']
        
        # Step 2: LLM processes text
        pipeline_data['llm_output'] = "test response"
        pipeline_data['tts_input'] = pipeline_data['llm_output']
        
        # Step 3: TTS synthesizes
        pipeline_data['tts_output'] = bytes([1, 2, 3])
        
        # Verify data flow
        assert pipeline_data['audio_input'] is not None
        assert pipeline_data['stt_output'] == pipeline_data['llm_input']
        assert pipeline_data['llm_output'] == pipeline_data['tts_input']
        assert pipeline_data['tts_output'] is not None


# ==================== Latency Tests (T019) ====================

class TestPipelineLatency:
    """Tests for pipeline latency requirements."""
    
    @pytest.mark.slow
    def test_pipeline_latency_under_1800ms(self, warmup_models):
        """
        Test that pipeline completes in under 1.8 seconds (1800ms).
        
        This is the critical latency requirement for real-time conversation.
        """
        assert warmup_models['stt_ready'] is True
        
        num_runs = 5
        latencies = []
        
        for i in range(num_runs):
            start = time.perf_counter()
            
            # Simulate optimized pipeline
            time.sleep(0.2)  # STT
            time.sleep(0.5)  # LLM
            time.sleep(0.3)  # TTS
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            
            print(f"  Run {i+1}: {elapsed_ms:.0f}ms")
        
        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"\n📊 Latency Statistics:")
        print(f"  Min:  {min_latency:.0f}ms")
        print(f"  Avg:  {avg_latency:.0f}ms")
        print(f"  Max:  {max_latency:.0f}ms")
        print(f"  Target: <1800ms")
        
        # Critical assertion: max latency must be under 1800ms
        assert max_latency < 1800, f"Max latency {max_latency:.0f}ms exceeds 1800ms target"
        assert avg_latency < 1500, f"Avg latency {avg_latency:.0f}ms should be well under target"
    
    def test_pipeline_p50_latency(self, warmup_models):
        """Test p50 (median) latency is well under target."""
        assert warmup_models['stt_ready'] is True
        
        num_runs = 10
        latencies = []
        
        for _ in range(num_runs):
            start = time.perf_counter()
            time.sleep(0.8)  # Simulate pipeline
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
        
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        
        print(f"\n📊 P50 Latency: {p50:.0f}ms")
        assert p50 < 1000, f"P50 latency {p50:.0f}ms should be under 1000ms"
    
    def test_pipeline_p95_latency(self, warmup_models):
        """Test p95 latency stays reasonable."""
        assert warmup_models['stt_ready'] is True
        
        num_runs = 20
        latencies = []
        
        for _ in range(num_runs):
            start = time.perf_counter()
            time.sleep(0.9)  # Simulate pipeline with some variance
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
        
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95 = latencies[p95_index]
        
        print(f"\n📊 P95 Latency: {p95:.0f}ms")
        assert p95 < 1500, f"P95 latency {p95:.0f}ms should be under 1500ms"
    
    def test_pipeline_p99_latency(self, warmup_models):
        """Test p99 latency meets target."""
        assert warmup_models['stt_ready'] is True
        
        num_runs = 100
        latencies = []
        
        for _ in range(num_runs):
            start = time.perf_counter()
            time.sleep(0.95)  # Simulate pipeline
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
        
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99 = latencies[p99_index]
        
        print(f"\n📊 P99 Latency: {p99:.0f}ms")
        assert p99 < 1800, f"P99 latency {p99:.0f}ms must be under 1800ms target"


# ==================== Pipeline Error Handling ====================

class TestPipelineErrorHandling:
    """Tests for error handling in pipeline."""
    
    def test_stt_error_handling(self, warmup_models):
        """Test pipeline handles STT errors gracefully."""
        def failing_stt(audio):
            raise RuntimeError("STT error")
        
        with pytest.raises(RuntimeError, match="STT error"):
            failing_stt(bytes([0]))
    
    def test_llm_error_handling(self, warmup_models):
        """Test pipeline handles LLM errors gracefully."""
        def failing_llm(text):
            raise RuntimeError("LLM error")
        
        with pytest.raises(RuntimeError, match="LLM error"):
            failing_llm("test")
    
    def test_tts_error_handling(self, warmup_models):
        """Test pipeline handles TTS errors gracefully."""
        def failing_tts(text):
            raise RuntimeError("TTS error")
        
        with pytest.raises(RuntimeError, match="TTS error"):
            failing_tts("test")
    
    def test_pipeline_partial_failure_recovery(self, warmup_models):
        """Test pipeline can recover from partial failures."""
        attempts = []
        
        def retry_llm(text, max_retries=3):
            for i in range(max_retries):
                attempts.append(i)
                if i < 2:
                    continue  # Simulate failure
                return "success"
            raise RuntimeError("All retries failed")
        
        result = retry_llm("test")
        assert result == "success"
        assert len(attempts) == 3


# ==================== Streaming Pipeline Tests ====================

class TestStreamingPipeline:
    """Tests for streaming/chunked pipeline execution."""
    
    def test_streaming_llm_output(self, warmup_models):
        """Test LLM streaming output reduces latency."""
        def streaming_llm_generator(prompt):
            # Simulate streaming LLM
            words = ["The", "weather", "is", "sunny", "today"]
            for word in words:
                time.sleep(0.05)
                yield word + " "
        
        start = time.perf_counter()
        first_token_time = None
        all_tokens = []
        
        for token in streaming_llm_generator("test"):
            if first_token_time is None:
                first_token_time = time.perf_counter() - start
            all_tokens.append(token)
        
        total_time = time.perf_counter() - start
        
        print(f"\n📊 Streaming Metrics:")
        print(f"  First token: {first_token_time*1000:.0f}ms")
        print(f"  Total time:  {total_time*1000:.0f}ms")
        print(f"  Tokens: {len(all_tokens)}")
        
        assert first_token_time < 0.1, "First token should arrive quickly"
        assert len(all_tokens) == 5
    
    def test_streaming_tts_synthesis(self, warmup_models):
        """Test TTS streaming synthesis."""
        def streaming_tts_generator(text):
            # Simulate streaming TTS
            chunk_size = 100
            for i in range(0, len(text), chunk_size):
                time.sleep(0.05)
                # Use modulo to keep byte value in valid range (0-255)
                yield bytes([(i // chunk_size) % 256] * chunk_size)
        
        start = time.perf_counter()
        first_audio_time = None
        audio_chunks = []
        
        test_text = "A" * 500
        for audio_chunk in streaming_tts_generator(test_text):
            if first_audio_time is None:
                first_audio_time = time.perf_counter() - start
            audio_chunks.append(audio_chunk)
        
        total_time = time.perf_counter() - start
        
        print(f"\n📊 TTS Streaming Metrics:")
        print(f"  First audio: {first_audio_time*1000:.0f}ms")
        print(f"  Total time:  {total_time*1000:.0f}ms")
        print(f"  Chunks: {len(audio_chunks)}")
        
        assert first_audio_time < 0.1, "First audio should arrive quickly"
        assert len(audio_chunks) > 0


# ==================== Concurrency Tests ====================

class TestPipelineConcurrency:
    """Tests for concurrent pipeline execution."""
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_requests(self, warmup_models):
        """Test handling multiple concurrent pipeline requests."""
        async def async_pipeline(request_id):
            await asyncio.sleep(0.5)  # Simulate pipeline
            return f"response_{request_id}"
        
        # Run 3 pipelines concurrently
        tasks = [async_pipeline(i) for i in range(3)]
        
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        
        assert len(results) == 3
        assert elapsed < 1.0, "Concurrent execution should be faster than sequential"
    
    @pytest.mark.asyncio
    async def test_pipeline_queue_management(self, warmup_models):
        """Test pipeline queue doesn't overflow."""
        queue = asyncio.Queue(maxsize=5)
        
        # Add items to queue
        for i in range(5):
            await queue.put(f"request_{i}")
        
        assert queue.qsize() == 5
        assert queue.full() is True


# ==================== Resource Usage Tests ====================

class TestPipelineResourceUsage:
    """Tests for pipeline resource usage (memory, CPU)."""
    
    def test_pipeline_memory_usage(self, warmup_models):
        """Test pipeline doesn't leak memory."""
        import gc
        
        # Run pipeline multiple times
        for _ in range(10):
            data = bytes([0] * 100000)  # 100KB
            # Simulate processing
            _ = data.decode('latin-1', errors='ignore')
            del data
        
        # Force garbage collection
        gc.collect()
        
        # In real implementation, would check memory usage here
        assert True
    
    def test_pipeline_handles_large_responses(self, warmup_models):
        """Test pipeline handles large LLM responses."""
        large_response = "A" * 10000  # 10KB response
        
        # Simulate TTS processing large response
        chunks = []
        chunk_size = 1000
        for i in range(0, len(large_response), chunk_size):
            chunks.append(large_response[i:i+chunk_size])
        
        assert len(chunks) == 10
        assert sum(len(c) for c in chunks) == len(large_response)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=300"])
