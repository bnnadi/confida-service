# Product Context

## Why This Project Exists

Confida is an **AI-powered interview coaching platform** that helps job seekers prepare for interviews. The API service orchestrates data flow between the frontend, AI service, and persistence layers.

## Problems Solved

- **Question generation** — Relevant interview questions based on role and job description
- **Answer evaluation** — Detailed feedback with scoring and improvement suggestions
- **Practice flexibility** — Both generic practice scenarios and job-specific interview prep
- **Real-time feedback** — Live speech analysis during mock interviews

## Target Users

Job seekers preparing for technical, behavioral, and situational interview questions across roles (Software Engineer, Data Scientist, Product Manager, Sales, Marketing, etc.).

## User Flows

1. **Parse job description** — Submit role + JD → receive tailored questions
2. **Create session** — Choose practice (scenario-based) or interview (job-based) mode
3. **Answer questions** — Record or type answers
4. **Analyze answers** — Get feedback, scores, and suggestions
5. **Real-time feedback** — WebSocket for live speech metrics (pace, clarity, filler words)
6. **Analytics** — View performance trends and dashboard insights

## Dual-Mode System

- **Practice mode** — Pre-defined scenarios (software_engineer, data_scientist, product_manager, sales_representative, marketing_manager) with curated questions
- **Interview mode** — AI-generated questions from job title + description

Both modes share scoring, feedback, and session management. See [docs/DUAL_MODE_FEATURES.md](../docs/DUAL_MODE_FEATURES.md).

## Scoring System

- **100-point scale** across 5 categories
- **17 sub-dimensions** for granular evaluation
- **Grade tiers:** Excellent (90–100), Strong (75–89), Average (60–74), At Risk (0–59)
- **Categories:** Verbal Communication (40), Interview Readiness (20), Non-verbal Communication (25), Adaptability & Engagement (15)

## UX Goals

- Unified experience across practice and interview modes
- Consistent API for frontend integration
- CORS configured for React
- Rate limiting and security headers
