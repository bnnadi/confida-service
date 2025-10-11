# Incomplete Flow & Missing UI Tickets

## Trigger
Command: `/tickets`

## Description
When triggered, I will:
- Inspect the codebase for **incomplete or broken flows**, such as partially implemented API calls, TODO/FIXME comments, and stubbed functions.  
- Check for **missing modals, dialogs, or pages** referenced in the code but not fully implemented.  
- Verify whether navigation flows (e.g., asset creation wizard, KYC templates, onboarding) reach a completed end state or break mid-way.  
- Identify **UI components that are referenced but not imported** or **routes that exist but lead to empty screens**.  

## Output
- A set of **tickets formatted in Markdown for Linear** with the following sections:  
  - **Title**  
  - **Type** (Bug / Feature / Enhancement)  
  - **Priority** (High / Medium / Low)  
  - **Description** (summary of the issue or gap, with file references where possible)  
  - **Current Behavior** (what is happening now)  
  - **Expected Behavior** (what should happen)  
  - **Acceptance Criteria** (clear pass/fail conditions)  
  - **Testing Steps** (steps to validate fix)  
  - **Dependencies** (other tickets, APIs, or components needed)  
  - **Estimation** (time/complexity sizing)  
  - **Notes** (extra implementation detail if relevant)  

## Example Ticket

**Title:** KYC Template Flow Broken  
**Type:** Bug  
**Priority:** High  
**Description:** `KYCForm.tsx` is missing validation and the "Submit" button does not trigger the API call.  
**Current Behavior:** User fills out the KYC template but form submission does not persist data.  
**Expected Behavior:** Valid KYC data should be submitted, saved in the backend, and displayed in the dashboard.  
**Acceptance Criteria:**  
- Form submission works with API  
- Validation errors displayed for invalid fields  
- Successful submission redirects user to dashboard  
**Testing Steps:**  
1. Fill out the KYC form with valid data  
2. Submit form  
3. Verify data persists to DB  
4. Confirm redirect to dashboard on success  
**Dependencies:** KYC API endpoint must be functional  
**Estimation:** 5 points  
**Notes:** Cross-check with backend validation schema to ensure consistency  

---

**Title:** Create Asset Flow Not Functional  
**Type:** Bug  
**Priority:** High  
**Description:** `CreateAssetWizard.tsx` ends after step 2 with no persistence logic.  
**Current Behavior:** Users cannot complete asset creation flow.  
**Expected Behavior:** Users should be able to create assets end-to-end, persist them, and see a success confirmation.  
**Acceptance Criteria:**  
- All wizard steps are implemented  
- Assets persist to DB  
- Success modal is shown on completion  
**Testing Steps:**  
1. Start the asset creation wizard  
2. Fill in required details through all steps  
3. Submit asset creation  
4. Confirm new asset appears in DB and UI  
**Dependencies:** Asset API endpoints and DB schema updates  
**Estimation:** 8 points  
**Notes:** Ensure proper error handling for failed persistence