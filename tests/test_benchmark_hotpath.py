from __future__ import annotations

import time
import statistics
from pydantic import BaseModel

from logicfp import protect, create_protector
from logicfp.domain.models import HandlerRequest


class SimpleInput(BaseModel):
    value: int


class SimpleOutput(BaseModel):
    result: int


def _measure_ops(func, payload, *, warmup=200, iterations=2000):
    for _ in range(warmup):
        func(payload=payload)
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        func(payload=payload)
        elapsed = time.perf_counter_ns() - start
        times.append(elapsed)
    return times


def _report(label, times_ns):
    times_us = [t / 1000 for t in times_ns]
    p50 = statistics.median(times_us)
    p95 = sorted(times_us)[int(len(times_us) * 0.95)]
    p99 = sorted(times_us)[int(len(times_us) * 0.99)]
    mean = statistics.mean(times_us)
    return {
        "label": label,
        "mean_us": round(mean, 1),
        "p50_us": round(p50, 1),
        "p95_us": round(p95, 1),
        "p99_us": round(p99, 1),
        "ops_per_sec": int(1_000_000 / mean) if mean > 0 else 0,
    }


def test_benchmark_bare_function_no_model():
    @protect(simple=True)
    def bare(request: HandlerRequest):
        return {"result": request.payload["value"] + 1}

    times = _measure_ops(bare, {"value": 42})
    report = _report("bare_no_model", times)
    print(f"\n[BENCH] {report}")
    assert report["p95_us"] < 5000, f"p95 too slow: {report['p95_us']} us"


def test_benchmark_bare_function_simple_false():
    @protect(simple=False)
    def bare(request: HandlerRequest):
        return {"result": request.payload["value"] + 1}

    times = _measure_ops(bare, {"value": 42})
    report = _report("bare_simple_false", times)
    print(f"\n[BENCH] {report}")
    assert report["p95_us"] < 5000, f"p95 too slow: {report['p95_us']} us"


def test_benchmark_with_input_output_model():
    @protect(input_model=SimpleInput, output_model=SimpleOutput, simple=False)
    def validated(request: HandlerRequest):
        return {"result": request.payload["value"] + 1}

    times = _measure_ops(validated, {"value": 42})
    report = _report("with_pydantic_models", times)
    print(f"\n[BENCH] {report}")
    assert report["p95_us"] < 5000, f"p95 too slow: {report['p95_us']} us"


def test_benchmark_shared_protector_no_model():
    protector = create_protector(default_source="bench")

    @protector.protect(simple=True)
    def shared(request: HandlerRequest):
        return {"result": request.payload["value"] + 1}

    times = _measure_ops(shared, {"value": 42})
    report = _report("shared_protector_no_model", times)
    print(f"\n[BENCH] {report}")
    assert report["p95_us"] < 5000, f"p95 too slow: {report['p95_us']} us"


def test_benchmark_overhead_breakdown():
    import uuid
    from datetime import datetime, timezone
    from dataclasses import asdict
    from logicfp.domain.models import RequestContext

    iterations = 5000

    start = time.perf_counter_ns()
    for _ in range(iterations):
        uuid.uuid4()
        uuid.uuid4()
    uuid_ns = (time.perf_counter_ns() - start) / iterations

    start = time.perf_counter_ns()
    for _ in range(iterations):
        datetime.now(timezone.utc).isoformat()
    datetime_ns = (time.perf_counter_ns() - start) / iterations

    ctx = RequestContext(
        request_id="req-1", trace_id="trace-1", source="bench",
        timestamp="2025-01-01T00:00:00Z",
    )
    start = time.perf_counter_ns()
    for _ in range(iterations):
        asdict(ctx)
    asdict_ns = (time.perf_counter_ns() - start) / iterations

    report = {
        "2x_uuid4_us": round(uuid_ns / 1000, 2),
        "datetime_iso_us": round(datetime_ns / 1000, 2),
        "asdict_context_us": round(asdict_ns / 1000, 2),
        "estimated_overhead_us": round((uuid_ns + datetime_ns + asdict_ns) / 1000, 2),
    }
    print(f"\n[BENCH overhead] {report}")
    assert True
