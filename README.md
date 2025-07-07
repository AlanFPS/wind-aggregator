# Wind-Damage Photo Aggregator ⛈️

A serverless micro-service that ingests up to 100 exterior-damage JPEG URLs and returns a single, claim-level wind-damage summary.  
Built for the **“Wind-Damage Photo Aggregator” coding assessment** — all requirements are met with Terraform IaC, Python 3.11 on AWS Lambda, and Amazon Rekognition for vision.

---

## 🛠️ Prerequisites

| Tool                   | Notes                                                                                        |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| **AWS CLI**            | Authenticated to your own AWS account (default region us-east-1 or adjust in `iac/main.tf`). |
| **Terraform ≥ 1.5**    | For one-command deploy/teardown.                                                             |
| **Python 3.11**        | Only needed if you want to rebuild the layer; pre-built wheels are already vendored.         |
| **PowerShell or cURL** | Invocation examples below use PowerShell but any HTTP client works.                          |

_No other services (DB, S3, etc.) are required; Lambda’s `/tmp` is the only scratch space._

---

## 🚀 One-command deploy

```powershell
# from repo root
terraform -chdir=iac init        # first time only
terraform -chdir=iac apply -auto-approve
```

Terraform outputs the public invoke URL:
invoke_url = "https://xxxxx.execute-api.us-east-1.amazonaws.com"

## 📡 Invoke the API

Example

```powershell
$invoke = (terraform -chdir=iac output -raw invoke_url).Trim()
Invoke-RestMethod "$invoke/aggregate" -Method POST `
-ContentType 'application/json' -InFile test/sample_request.json |
ConvertTo-Json -Depth 5
```

cURL equivalent

```bash
curl -X POST "$INVOKE_URL/aggregate" \
 -H 'Content-Type: application/json' \
 -d @test/sample_request.json
Successful response (200 OK) is a JSON document matching the schema in test/sample_response.json.
```

Error cases:

- HTTP code Reason
- 422 images array empty or missing.
- 500 Unhandled error — body includes "correlation_id" for log tracing.

## 🧹 Teardown

```powershell
terraform -chdir=iac destroy -auto-approve
```

This removes the Lambda, API Gateway, IAM role, and layer.

## 📖 Assumptions & implementation notes

- Vision model: Amazon Rekognition DetectLabels with MinConfidence = 40.
- Damage detection: any label whose name matches the case-insensitive regex
  "(damage|crack|broken|missing|tear|dent|roof damage|home damage)".
  The highest matching confidence becomes damage_conf.
- Severity mapping - severity = int(damage_conf / 20) → range 0-4 (capped at 4).
- Area mapping: simple label→area dictionary (Roof, Shingle, Siding, Garage, …).
- Quality filters:
  Blur: Laplacian variance (threshold = 250).
  Brightness: gray-mean (threshold = 5).
  Deduplication: perceptual dhash with Hamming distance ≤ 6; sharpest in cluster kept.
- Business rule: damage_confirmed = true if ≥ 2 photos of an area have severity ≥ 2.
- Areas with any damage are still returned even if not confirmed.
- Overall severity: weighted mean of severity × quality_score across all analyzed photos.
- Confidence heuristic: base 0.5 + (confirmed-areas ratio × 0.5), clamped 0-1.
- No persistence: everything runs in-memory; temp files live in /tmp and are discarded after execution.
- Logging: every request gets a UUID correlation_id; CloudWatch logs include quality scores and raw Rekognition labels for tuning.

## ✅ Current status vs assessment checklist

All functional and infrastructure requirements are satisfied.

Remaining polish: choose best representative image per area, tune quality thresholds further.
