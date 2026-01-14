# Citation Verification Strategies

This document provides detailed strategies for implementing citation verification in production RAG systems, balancing quality and latency trade-offs.

---

## 1. The Latency vs Quality Tradeoff

Citation verification improves answer quality but adds latency. The challenge:

| Component | Typical Latency |
|-----------|-----------------|
| Retrieval | 200-500ms |
| Generation | 1-2s |
| **Citation Verification** | **1-3s** ⚠️ |
| **Total** | **2.5-5.5s** |

For interactive use cases, 5.5s is often unacceptable. The following strategies balance quality and speed.

---

## 2. Strategy 1: Async/Background Verification

**Approach:** Return answer immediately, verify in background

**Best for:** Audit trails, quality monitoring, non-blocking workflows

### Implementation

```python
import asyncio
from datetime import datetime
from typing import Optional

@app.post("/query")
async def query(request: QueryRequest):
    """Return answer immediately, verify asynchronously."""
    
    # Generate answer with citations
    response = await generate_answer(request.question)
    
    # Return immediately with pending status
    response_with_id = AnswerResponse(
        request_id=response.id,
        answer=response.answer,
        sources=response.sources,
        verification_status="pending",  # Not verified yet
        created_at=datetime.utcnow()
    )
    
    # Start background verification (don't await)
    asyncio.create_task(verify_and_store(response))
    
    return response_with_id


async def verify_and_store(response: Answer):
    """Background task: verify citations and store results."""
    try:
        verification = await verify_citations_with_llm(response)
        
        # Store verification results
        await db.store_verification(
            request_id=response.id,
            verification=verification,
            verified_at=datetime.utcnow()
        )
        
        # Optional: notify if verification fails
        if not verification.is_valid:
            await alert_low_quality_response(response.id)
            
    except Exception as e:
        logger.error(f"Verification failed for {response.id}: {e}")


# Expose verification results via separate endpoint
@app.get("/query/{request_id}/verification")
async def get_verification(request_id: str):
    """Get verification status for a previous query."""
    
    verification = await db.get_verification(request_id)
    
    if not verification:
        return {"status": "pending"}
    
    return {
        "status": "completed",
        "verified_at": verification.verified_at,
        "is_valid": verification.is_valid,
        "grounding_score": verification.grounding_score,
        "issues": verification.issues
    }
```

### Real-Time Updates (Optional)

```python
from fastapi import WebSocket

@app.websocket("/ws/query/{request_id}")
async def websocket_verification(websocket: WebSocket, request_id: str):
    """Stream verification updates via WebSocket."""
    await websocket.accept()
    
    # Wait for verification to complete
    verification = await wait_for_verification(request_id, timeout=10)
    
    await websocket.send_json({
        "type": "verification_complete",
        "data": verification.dict()
    })
    
    await websocket.close()
```

**Latency Impact:** ✅ None (user gets answer in ~2s)  
**Quality:** ⚠️ User doesn't know if answer is verified initially

---

## 3. Strategy 2: Selective Verification

**Approach:** Verify only when needed based on risk signals

**Best for:** Production systems with mixed-criticality queries

### Implementation

```python
from enum import Enum

class VerificationTrigger(Enum):
    """Signals that indicate verification is needed."""
    LOW_CONFIDENCE = "low_confidence"
    WEAK_SOURCES = "weak_sources"
    HIGH_STAKES = "high_stakes"
    ALWAYS = "always"


async def generate_with_smart_verification(
    question: str,
    verification_mode: str = "auto"
) -> AnswerResponse:
    """Generate answer with adaptive verification."""
    
    # Generate answer
    response = await generate_answer(question)
    
    # Determine if verification needed
    triggers = []
    
    if response.grounding_score < 0.75:
        triggers.append(VerificationTrigger.LOW_CONFIDENCE)
    
    if any(source.score < 0.6 for source in response.sources):
        triggers.append(VerificationTrigger.WEAK_SOURCES)
    
    if is_high_stakes_query(question):
        triggers.append(VerificationTrigger.HIGH_STAKES)
    
    # Decide verification strategy
    should_verify_sync = (
        verification_mode == "always" or
        len(triggers) > 0
    )
    
    if should_verify_sync:
        # Synchronous verification for risky queries
        response.verification = await verify_citations(response)
        response.verification_triggers = [t.value for t in triggers]
    else:
        # Fast path: skip verification
        response.verification = {"status": "skipped"}
        
        # Still verify async for monitoring
        asyncio.create_task(verify_and_log_async(response))
    
    return response


def is_high_stakes_query(question: str) -> bool:
    """Detect queries requiring extra care."""
    high_stakes_keywords = [
        "legal", "compliance", "regulation",
        "policy", "contract", "liability",
        "safety", "medical", "financial"
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in high_stakes_keywords)
```

**Latency Impact:** ✅ Fast for most queries (~2s), slow for risky ones (~5s)  
**Quality:** ✅ High-risk queries get full validation

---

## 4. Strategy 3: Cached Verification

**Approach:** Pre-verify common queries offline

**Best for:** FAQ-style use cases with repeated queries

### Implementation

```python
import hashlib
from typing import Optional
from datetime import datetime, timedelta

class VerificationCache:
    """Cache for pre-verified queries."""
    
    def __init__(self, redis_client):
        self.cache = redis_client
        self.ttl = timedelta(hours=24)
    
    def get_query_hash(self, question: str) -> str:
        """Generate stable hash for query."""
        normalized = question.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def get(self, question: str) -> Optional[dict]:
        """Get cached verified response."""
        key = f"verified:{self.get_query_hash(question)}"
        cached = await self.cache.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def set(self, question: str, response: dict):
        """Cache verified response."""
        key = f"verified:{self.get_query_hash(question)}"
        await self.cache.setex(
            key,
            int(self.ttl.total_seconds()),
            json.dumps(response)
        )


# Initialize cache
verification_cache = VerificationCache(redis_client)


# Offline: Pre-verify popular queries
async def precompute_verified_answers():
    """Background job: verify common queries."""
    
    popular_queries = await get_popular_queries(limit=100)
    
    for query in popular_queries:
        # Generate and verify
        response = await generate_answer(query)
        verification = await verify_citations(response)
        
        # Cache the verified response
        await verification_cache.set(query, {
            "response": response.dict(),
            "verification": verification.dict(),
            "verified_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Pre-verified query: {query[:50]}...")


# Online: Use cache when available
@app.post("/query")
async def query_with_cache(request: QueryRequest):
    """Check cache, fallback to generation."""
    
    # Check cache first
    cached = await verification_cache.get(request.question)
    
    if cached:
        logger.info(f"Cache hit for: {request.question[:50]}...")
        return {
            **cached["response"],
            "cache_hit": True,
            "verified_at": cached["verified_at"]
        }
    
    # Cache miss: generate new response
    response = await generate_answer(request.question)
    
    # Verify async and cache for future
    asyncio.create_task(
        verify_and_cache(request.question, response)
    )
    
    return response


async def verify_and_cache(question: str, response: Answer):
    """Verify and cache for future requests."""
    verification = await verify_citations(response)
    
    await verification_cache.set(question, {
        "response": response.dict(),
        "verification": verification.dict(),
        "verified_at": datetime.utcnow().isoformat()
    })
```

**Latency Impact:** ✅ Instant for cached queries (<100ms), normal for new (~2s)  
**Quality:** ✅ Popular queries always verified

---

## 5. Strategy 4: Hybrid Fast + Deep Verification

**Approach:** Quick checks inline, deep verification async

**Best for:** Real-time systems needing some quality assurance

### Implementation

```python
from dataclasses import dataclass
from typing import List

@dataclass
class QuickCheck:
    """Fast heuristic verification results."""
    all_claims_cited: bool
    sources_nonempty: bool
    no_empty_citations: bool
    no_obvious_contradictions: bool
    
    @property
    def is_clean(self) -> bool:
        """All checks passed."""
        return all([
            self.all_claims_cited,
            self.sources_nonempty,
            self.no_empty_citations,
            self.no_obvious_contradictions
        ])
    
    @property
    def has_red_flags(self) -> bool:
        """Critical issues detected."""
        return not self.sources_nonempty or not self.no_empty_citations


def quick_citation_check(response: Answer) -> QuickCheck:
    """Fast sanity checks (~50-100ms)."""
    
    answer = response.answer
    sources = response.sources
    
    # Check 1: Citation markers present
    citation_markers = ["[", "]", "source:", "according to"]
    has_citations = any(marker in answer.lower() for marker in citation_markers)
    
    # Check 2: Sources not empty
    sources_nonempty = len(sources) > 0
    
    # Check 3: No empty citation references
    no_empty_citations = "[Source: ]" not in answer
    
    # Check 4: Simple contradiction detection
    contradictions = detect_simple_contradictions(answer)
    no_contradictions = len(contradictions) == 0
    
    return QuickCheck(
        all_claims_cited=has_citations,
        sources_nonempty=sources_nonempty,
        no_empty_citations=no_empty_citations,
        no_obvious_contradictions=no_contradictions
    )


def detect_simple_contradictions(text: str) -> List[str]:
    """Detect obvious contradictions via pattern matching."""
    contradictions = []
    
    # Look for negation patterns
    if "yes" in text.lower() and "no" in text.lower():
        if text.lower().find("yes") < text.lower().find("no"):
            contradictions.append("yes/no conflict")
    
    # Look for conflicting numbers
    import re
    numbers = re.findall(r'\d+', text)
    if len(numbers) > 1 and len(set(numbers)) > 1:
        # Multiple different numbers (possible conflict)
        pass  # More sophisticated check needed
    
    return contradictions


async def verify_citations_with_llm(response: Answer) -> VerificationResult:
    """Deep LLM-based verification (~1-3s)."""
    
    verification_prompt = f"""
You are a citation verifier. Evaluate if the answer's claims are supported by the sources.

Answer: {response.answer}

Sources:
{format_sources_for_verification(response.sources)}

For each claim in the answer:
1. Identify the claim
2. Check if a source supports it
3. Rate support: STRONG, WEAK, or UNSUPPORTED

Return JSON with:
{{
  "claims": [
    {{"claim": "...", "support": "STRONG", "source_id": 1}},
    ...
  ],
  "overall_score": 0.0-1.0,
  "issues": ["..."]
}}
"""
    
    result = await llm.generate(verification_prompt, response_format="json")
    return VerificationResult.parse(result)


@app.post("/query")
async def query_with_hybrid_verification(request: QueryRequest):
    """Fast basic checks + conditional deep verification."""
    
    # Generate answer
    response = await generate_answer(request.question)
    
    # Quick check (< 100ms)
    quick_check = quick_citation_check(response)
    response.metadata["quick_check"] = quick_check.__dict__
    
    # Decide on deep verification
    if quick_check.has_red_flags:
        # Critical issue: verify synchronously
        logger.warning(f"Red flags detected, deep verification required")
        response.verification = await verify_citations_with_llm(response)
        
    elif not quick_check.is_clean:
        # Minor issues: verify async
        logger.info(f"Issues detected, async verification scheduled")
        asyncio.create_task(deep_verify_and_log(response))
        response.verification = {"status": "pending", "quick_check": "passed_with_warnings"}
        
    else:
        # Clean: skip sync verification
        asyncio.create_task(deep_verify_and_log(response))
        response.verification = {"status": "pending", "quick_check": "clean"}
    
    return response
```

**Latency Impact:** ✅ Adds only ~100ms for most queries  
**Quality:** ✅ Catches major issues synchronously, monitors all responses

---

## 6. Strategy 5: Tiered Response Strategy

**Approach:** Offer different SLAs based on query tier

**Best for:** Enterprise systems with different use cases

### Implementation

```python
from enum import Enum

class QueryTier(Enum):
    """Query processing tiers."""
    FAST = "fast"          # No verification, ~2s
    BALANCED = "balanced"  # Async verification, ~2s
    VERIFIED = "verified"  # Sync verification, ~5s


@app.post("/query")
async def query(
    request: QueryRequest,
    tier: QueryTier = QueryTier.BALANCED
):
    """Process query with tier-based verification."""
    
    response = await generate_answer(request.question)
    
    if tier == QueryTier.VERIFIED:
        # High-stakes: full synchronous verification
        response.verification = await verify_citations_with_llm(response)
        response.tier = "verified"
        
    elif tier == QueryTier.BALANCED:
        # Default: quick check + async deep verification
        quick_check = quick_citation_check(response)
        response.quick_check = quick_check.__dict__
        
        asyncio.create_task(verify_and_store(response))
        response.verification = {"status": "pending"}
        response.tier = "balanced"
        
    else:  # FAST
        # Speed priority: no verification
        response.verification = {"status": "skipped"}
        response.tier = "fast"
    
    response.metadata["tier"] = tier.value
    return response
```

**Latency by Tier:**

| Tier | Latency | Use Case |
|------|---------|----------|
| Fast | ~2s | Exploratory queries, low stakes |
| Balanced | ~2s + async | Default, most queries |
| Verified | ~5s | Legal, compliance, high stakes |

---

## 7. Recommended Production Approach

**Combine Strategy 2 (Selective) + Strategy 4 (Hybrid):**

```python
async def generate_answer_with_citation_quality(
    question: str,
    force_verification: bool = False
) -> AnswerResponse:
    """Production-grade answer generation with adaptive verification."""
    
    # 1. Generate answer
    response = await generate_answer(question)
    
    # 2. Fast sanity check (always run, ~100ms)
    basic_check = quick_citation_check(response)
    response.metadata["basic_verification"] = basic_check.__dict__
    
    # 3. Decide on deep verification
    needs_deep_verification = (
        force_verification or
        basic_check.has_red_flags or
        response.grounding_score < 0.75 or
        is_high_stakes_query(question)
    )
    
    if needs_deep_verification:
        # Synchronous deep verification
        logger.info(f"Deep verification required for: {question[:50]}...")
        response.verification = await verify_citations_with_llm(response)
        
    else:
        # Quick path: async verification for monitoring
        asyncio.create_task(verify_and_log_async(response))
        response.verification = {
            "status": "pending",
            "basic_check": "passed"
        }
    
    return response


async def verify_and_log_async(response: Answer):
    """Background verification for quality monitoring."""
    try:
        verification = await verify_citations_with_llm(response)
        
        # Log to monitoring system
        await log_verification_metrics(response.id, verification)
        
        # Alert on quality issues
        if verification.overall_score < 0.7:
            await alert_low_quality(response.id, verification)
            
    except Exception as e:
        logger.error(f"Background verification failed: {e}")
```

**Why this works:**

✅ **Fast default path** (~2-2.5s) - most queries stay fast  
✅ **Safety net** - critical issues caught synchronously  
✅ **Quality monitoring** - all queries eventually verified  
✅ **Flexible** - can force full verification when needed  
✅ **Cost-effective** - deep LLM verification only when necessary

---

## 8. Implementation Priorities

### Phase 1: Foundation (Week 1)
- [ ] Implement `quick_citation_check()` with basic heuristics
- [ ] Add basic verification metadata to responses
- [ ] Create background task infrastructure for async verification

### Phase 2: Deep Verification (Week 2)
- [ ] Implement `verify_citations_with_llm()` with LLM-as-judge
- [ ] Add verification result storage
- [ ] Create `/query/{id}/verification` endpoint

### Phase 3: Intelligent Routing (Week 3)
- [ ] Implement selective verification logic
- [ ] Add high-stakes query detection
- [ ] Create verification cache for common queries

### Phase 4: Production Hardening (Week 4)
- [ ] Add monitoring and alerting for low-quality responses
- [ ] Implement tiered verification options
- [ ] Performance optimization and load testing

---

## 9. Monitoring Citation Quality

Track these metrics in your observability system:

```python
# Metrics to track
verification_latency = Histogram(
    'citation_verification_duration_seconds',
    'Time spent on citation verification'
)

verification_score = Histogram(
    'citation_verification_score',
    'Overall verification score distribution'
)

verification_failures = Counter(
    'citation_verification_failures_total',
    'Failed verifications',
    ['reason']
)

# In verification code
with verification_latency.time():
    result = await verify_citations_with_llm(response)

verification_score.observe(result.overall_score)

if result.overall_score < 0.7:
    verification_failures.labels(reason='low_score').inc()
```

**Key questions to answer:**
- What % of queries need deep verification?
- What's the average verification score?
- Which query types have lowest scores?
- Is verification latency acceptable?
