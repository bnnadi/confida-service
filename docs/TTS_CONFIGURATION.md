# TTS (Text-to-Speech) Configuration Guide

## Overview

The Confida service supports multiple TTS providers for generating voice audio from text. The system uses a provider abstraction layer that allows switching between local and cloud-based TTS services with automatic fallback support.

## Cost Comparison

### Quick Cost Overview

| Provider | Cost Model | Free Tier | Entry Plan | Best For |
|----------|-----------|-----------|------------|----------|
| **Coqui** | Free (self-hosted) | Unlimited | $0/month | Development, low-cost production |
| **ElevenLabs** | Credits (per character) | 10K credits/month | $5/month (30K credits) | High-quality production |
| **PlayHT** | Subscription | Limited free | $39/month (Creator) | Enterprise features |

### Detailed Pricing

#### Coqui TTS
- **Cost:** $0 (completely free, open-source)
- **Limitations:** None (self-hosted)
- **Infrastructure Costs:** Server/GPU resources (if using GPU acceleration)
- **Best For:** Unlimited usage without per-character costs

#### ElevenLabs
- **Free Plan:** $0/month
  - 10,000 credits/month (~10 minutes of audio)
  - Good for testing and low-volume usage
  
- **Starter Plan:** $5/month
  - 30,000 credits/month (~30 minutes)
  - Commercial license included
  
- **Creator Plan:** $22/month
  - 100,000 credits/month (~100 minutes)
  - Professional voice cloning
  
- **Pro Plan:** $99/month
  - 500,000 credits/month (~500 minutes)
  - 44.1kHz PCM audio via API
  
- **Scale Plan:** $330/month
  - 2,000,000 credits/month (~2,000 minutes)
  - Multi-seat workspace
  
- **Business Plan:** $1,320/month
  - 11,000,000 credits/month (~11,000 minutes)
  - Low-latency TTS, professional voice clones

**Credit System:** Approximately 1 credit = 1 character for standard TTS. Credits are consumed based on text length.

**Cost Per Character:** 
- Free: $0 (limited to 10K/month)
- Starter: ~$0.00017 per character ($5 ÷ 30,000)
- Creator: ~$0.00022 per character ($22 ÷ 100,000)
- Pro: ~$0.00020 per character ($99 ÷ 500,000)
- Scale: ~$0.00017 per character ($330 ÷ 2,000,000)
- Business: ~$0.00012 per character ($1,320 ÷ 11,000,000)

#### PlayHT
- **Free Plan:** $0/month
  - Limited usage (check current limits)
  
- **Creator Plan:** $39/month (or $31/month annual)
  - Unlimited plan available
  
- **Unlimited Plan:** $99/month (or $29/month annual)
  - Unlimited TTS generation
  
- **Enterprise Plan:** Custom pricing
  - Contact sales for volume discounts

**Note:** PlayHT pricing structure may vary. Check [PlayHT pricing](https://play.ht) for current details.

### Cost Estimation Examples

#### Example 1: Development/Testing
- **Usage:** 1,000 questions/month, ~100 characters per question
- **Total:** 100,000 characters/month
- **Coqui:** $0 (free)
- **ElevenLabs Free:** ❌ Exceeds limit (10K credits)
- **ElevenLabs Starter:** $5/month (30K credits) - ❌ Insufficient
- **ElevenLabs Creator:** $22/month ✅
- **PlayHT Creator:** $39/month ✅

#### Example 2: Production (Medium Volume)
- **Usage:** 10,000 questions/month, ~150 characters per question
- **Total:** 1,500,000 characters/month
- **Coqui:** $0 (free, but requires server resources)
- **ElevenLabs Scale:** $330/month ✅
- **PlayHT Unlimited:** $99/month ✅ (if truly unlimited)

#### Example 3: High Volume Production
- **Usage:** 100,000 questions/month, ~200 characters per question
- **Total:** 20,000,000 characters/month
- **Coqui:** $0 (free, but significant server/GPU costs)
- **ElevenLabs Business:** $1,320/month ✅
- **PlayHT Enterprise:** Contact for pricing

### Cost Optimization Tips

1. **Use Coqui for Development:**
   - Zero API costs during development
   - Test extensively before switching to paid providers

2. **Implement Caching:**
   - Cache synthesized audio (default: 7 days)
   - Reduces API calls for repeated questions
   - Significant cost savings for common questions

3. **Monitor Usage:**
   - Track character/credit consumption
   - Set up alerts for unexpected usage spikes
   - Optimize question length where possible

4. **Choose Appropriate Plan:**
   - Start with lower tier, scale up as needed
   - Consider annual billing for discounts (PlayHT)
   - Use fallback to Coqui for cost savings

5. **Hybrid Approach:**
   - Use vendor provider for production
   - Fallback to Coqui if vendor fails
   - Reduces costs while maintaining quality

### Infrastructure Costs (Coqui)

While Coqui is free, consider:
- **CPU-only:** Minimal cost, slower synthesis
- **GPU:** Higher server costs, faster synthesis
- **Storage:** Audio file storage (minimal)
- **Bandwidth:** Audio delivery (varies by usage)

**Estimated Monthly Costs (Coqui on Cloud):**
- Small deployment (CPU): $20-50/month
- Medium deployment (GPU): $100-300/month
- Large deployment (GPU cluster): $500+/month

---

## Supported Providers

### 1. Coqui TTS (Default - Local)

**Provider ID:** `coqui`

**Description:** Open-source, local TTS solution that runs on your server. No API keys required.

**Cost:** $0/month (free, open-source)
- No per-character or per-request charges
- Only infrastructure costs (server/GPU if needed)
- Estimated: $20-300/month for cloud hosting depending on scale

**Advantages:**
- ✅ No API costs
- ✅ No rate limits
- ✅ Works offline
- ✅ Full control over voice models
- ✅ Privacy-friendly (data stays on your server)
- ✅ Unlimited usage without per-character fees

**Disadvantages:**
- ⚠️ Requires GPU for best performance
- ⚠️ May have lower voice quality compared to premium vendors
- ⚠️ Requires model downloads and storage
- ⚠️ Infrastructure costs (server/GPU hosting)

**Use Cases:**
- Development and testing
- Cost-sensitive deployments
- Privacy-critical applications
- Offline environments
- High-volume usage where infrastructure costs < API costs

**Configuration:**
```bash
TTS_PROVIDER=coqui
# No API keys required
```

---

### 2. ElevenLabs

**Provider ID:** `elevenlabs`

**Description:** Premium cloud-based TTS service known for high-quality, natural-sounding voices.

**Cost:** Usage-based (credits per character)
- **Free:** $0/month - 10,000 credits (~10 minutes)
- **Starter:** $5/month - 30,000 credits (~30 minutes)
- **Creator:** $22/month - 100,000 credits (~100 minutes)
- **Pro:** $99/month - 500,000 credits (~500 minutes)
- **Scale:** $330/month - 2M credits (~2,000 minutes)
- **Business:** $1,320/month - 11M credits (~11,000 minutes)
- **Cost per character:** ~$0.00012-0.00022 depending on plan

**Advantages:**
- ✅ Excellent voice quality and naturalness
- ✅ Fast API response times
- ✅ Wide variety of voices
- ✅ Good documentation and support
- ✅ Free tier for testing

**Disadvantages:**
- ⚠️ Requires API key and paid subscription for production
- ⚠️ Usage-based pricing (costs scale with usage)
- ⚠️ Rate limits apply
- ⚠️ Data sent to external service

**Use Cases:**
- Production applications requiring high-quality voices
- Applications where voice quality is critical
- When budget allows for premium TTS
- Low to medium volume usage

**Configuration:**
```bash
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your_api_key_here
```

**Getting an API Key:**
1. Sign up at [ElevenLabs](https://elevenlabs.io)
2. Navigate to your profile settings
3. Copy your API key
4. Set it in your environment variables

---

### 3. PlayHT

**Provider ID:** `playht`

**Description:** Cloud-based TTS service with enterprise features and multiple voice options.

**Cost:** Subscription-based
- **Free:** $0/month - Limited usage
- **Creator:** $39/month (or $31/month annual) - Unlimited plan available
- **Unlimited:** $99/month (or $29/month annual) - Unlimited TTS
- **Enterprise:** Custom pricing - Contact sales

**Advantages:**
- ✅ Good voice quality
- ✅ Enterprise features available
- ✅ Multiple voice options
- ✅ Reliable API
- ✅ Unlimited plans available (may be cost-effective for high volume)

**Disadvantages:**
- ⚠️ Requires both API key and User ID
- ⚠️ Higher entry cost than ElevenLabs
- ⚠️ Rate limits apply
- ⚠️ Data sent to external service

**Use Cases:**
- Production applications
- When ElevenLabs is not available in your region
- Enterprise deployments requiring specific features
- High-volume usage (unlimited plans)

**Configuration:**
```bash
TTS_PROVIDER=playht
PLAYHT_API_KEY=your_api_key_here
PLAYHT_USER_ID=your_user_id_here
```

**Getting Credentials:**
1. Sign up at [PlayHT](https://play.ht)
2. Navigate to your account settings
3. Copy your API key and User ID
4. Set them in your environment variables

---

## Provider Selection Strategy

### Default Configuration

The system defaults to **Coqui** (local TTS) to ensure:
- Zero-cost development and testing
- No external dependencies
- Privacy by default

### Production Recommendations

For production deployments, consider:

1. **Cost Optimization:** Use Coqui for development, vendor providers for production
2. **Quality Requirements:** Use ElevenLabs or PlayHT for high-quality voices
3. **Redundancy:** Configure a fallback provider for reliability
4. **Regional Availability:** Choose providers available in your deployment region

### Fallback Configuration

You can configure a fallback provider that will be used if the primary provider fails:

```bash
TTS_PROVIDER=elevenlabs
TTS_FALLBACK_PROVIDER=coqui
```

**Fallback Behavior:**
- If primary provider fails → automatically try fallback
- If fallback also fails → return error
- Circuit breaker prevents cascading failures

---

## Configuration Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_PROVIDER` | `coqui` | Primary TTS provider (`coqui`, `elevenlabs`, `playht`) |
| `TTS_FALLBACK_PROVIDER` | `` | Optional fallback provider |
| `TTS_DEFAULT_VOICE_ID` | `confida-default-en` | Default voice identifier |
| `TTS_VOICE_VERSION` | `1` | Voice model version number |
| `TTS_DEFAULT_FORMAT` | `mp3` | Audio format (`mp3`, `wav`, `ogg`, `m4a`, `aac`) |

### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_TIMEOUT` | `30` | Request timeout in seconds (1-300) |
| `TTS_RETRY_ATTEMPTS` | `3` | Number of retry attempts on failure (0-10) |
| `TTS_MAX_CONCURRENT` | `5` | Maximum concurrent synthesis requests (1-50) |
| `TTS_CACHE_TTL` | `604800` | Cache TTL in seconds (7 days) |

### Vendor API Keys

| Variable | Required When | Description |
|----------|----------------|-------------|
| `ELEVENLABS_API_KEY` | `TTS_PROVIDER=elevenlabs` | ElevenLabs API key |
| `PLAYHT_API_KEY` | `TTS_PROVIDER=playht` | PlayHT API key |
| `PLAYHT_USER_ID` | `TTS_PROVIDER=playht` | PlayHT user identifier |

---

## Configuration Examples

### Development Setup (Local TTS)

```bash
# Use local Coqui TTS - no API keys needed
TTS_PROVIDER=coqui
TTS_DEFAULT_VOICE_ID=confida-default-en
TTS_DEFAULT_FORMAT=mp3
TTS_CACHE_TTL=3600  # 1 hour for development
TTS_TIMEOUT=30
TTS_RETRY_ATTEMPTS=3
TTS_MAX_CONCURRENT=3
```

### Production Setup (Vendor Provider)

```bash
# Use ElevenLabs with Coqui as fallback
TTS_PROVIDER=elevenlabs
TTS_FALLBACK_PROVIDER=coqui
ELEVENLABS_API_KEY=your_production_key_here
TTS_DEFAULT_VOICE_ID=confida-default-en
TTS_DEFAULT_FORMAT=mp3
TTS_CACHE_TTL=604800  # 7 days
TTS_TIMEOUT=30
TTS_RETRY_ATTEMPTS=3
TTS_MAX_CONCURRENT=10
```

### High-Availability Setup

```bash
# Primary: ElevenLabs, Fallback: PlayHT, Emergency: Coqui
TTS_PROVIDER=elevenlabs
TTS_FALLBACK_PROVIDER=playht
ELEVENLABS_API_KEY=your_key
PLAYHT_API_KEY=your_key
PLAYHT_USER_ID=your_user_id
# Note: System will try playht if elevenlabs fails
# Coqui can be used as last resort (requires code changes)
```

---

## Extending with Additional Providers

The TTS system is designed to be extensible. To add a new provider:

1. **Implement the Base Interface:**
   ```python
   from app.services.tts.base import BaseTTSProvider
   
   class MyCustomTTSProvider(BaseTTSProvider):
       async def synthesize(self, text, voice_id, format="mp3"):
           # Implementation
           pass
   ```

2. **Update Configuration:**
   - Add provider name to `VALID_TTS_PROVIDERS` in `app/utils/validation.py`
   - Add any required API keys to `app/config.py`
   - Update `env.example` with new variables

3. **Update Factory:**
   - Add provider instantiation logic in `app/services/tts/factory.py`

4. **Add Tests:**
   - Create unit tests for the new provider
   - Update integration tests

**Common Providers You Might Add:**
- Google Cloud Text-to-Speech
- AWS Polly
- Azure Cognitive Services Speech
- OpenAI TTS (if available)

---

## Validation and Startup Checks

The system validates TTS configuration at startup:

### Errors (Prevent Startup)
- Invalid provider name
- Missing required API keys for selected provider
- Invalid numeric values (out of range)
- Invalid audio format

### Warnings (Allow Startup)
- API keys set but provider not used
- Very high cache TTL (>30 days)
- High concurrency settings (>20)
- Fallback provider same as primary
- Short API keys (potential issues)

**Example Startup Output:**
```
✅ Configuration validation passed
⚠️  Configuration warnings:
   - TTS_CACHE_TTL is very high (2592000 seconds = 30.0 days)
   - ELEVENLABS_API_KEY is set but TTS_PROVIDER is not 'elevenlabs'
```

---

## Best Practices

### 1. Development
- Use `coqui` (local) to avoid API costs
- Set shorter cache TTL for faster iteration
- Lower concurrency limits for resource conservation

### 2. Production
- Use vendor providers for quality
- Configure fallback provider for reliability
- Set appropriate cache TTL (7 days recommended)
- Monitor API usage and costs
- Use appropriate concurrency limits based on server capacity

### 3. Security
- Never commit API keys to version control
- Use environment variables or secret management
- Rotate API keys regularly
- Monitor for unauthorized usage

### 4. Performance
- Enable caching (default: 7 days)
- Use appropriate timeout values
- Set concurrency limits based on server capacity
- Monitor synthesis latency

---

## Troubleshooting

### Provider Not Working

1. **Check Configuration:**
   ```bash
   # Verify provider name is correct
   echo $TTS_PROVIDER
   ```

2. **Check API Keys:**
   ```bash
   # For ElevenLabs
   echo $ELEVENLABS_API_KEY
   
   # For PlayHT
   echo $PLAYHT_API_KEY
   echo $PLAYHT_USER_ID
   ```

3. **Check Startup Logs:**
   - Look for validation errors
   - Check for API key validation warnings

### High Latency

1. **Reduce Concurrency:**
   ```bash
   TTS_MAX_CONCURRENT=3  # Lower value
   ```

2. **Increase Timeout:**
   ```bash
   TTS_TIMEOUT=60  # Higher value
   ```

3. **Check Network:**
   - Verify connectivity to vendor APIs
   - Check firewall rules

### Cache Not Working

1. **Verify Cache Backend:**
   ```bash
   CACHE_ENABLED=true
   CACHE_BACKEND=redis  # or memory
   ```

2. **Check Cache TTL:**
   ```bash
   TTS_CACHE_TTL=604800  # Should be > 0
   ```

---

## Related Documentation

- [Environment Variables Guide](./environment-variables.md)
- [TTS Implementation Tickets](../tickets/TTS_IMPLEMENTATION_TICKETS.md)
- [API Service Contract](./AI_SERVICE_CONTRACT.md)

---

## Support

For issues or questions:
1. Check startup validation logs
2. Review configuration against this guide
3. Verify API keys are valid
4. Check provider status pages (ElevenLabs, PlayHT)

