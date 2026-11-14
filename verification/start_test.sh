#!/bin/bash
# Start-up stability test for image v3. Deploys N throwaway no-traffic revisions of the SAME image (only a NONCE env var differs),
# so each one is a genuine fresh container start, then requests the tagged URL of each.
# usage: bash start_test.sh <N>
N=${1:-8}
P=goats-hsw-rag-1110; R=asia-southeast1; S=goats-hsw-rag-chatbot
IMG=asia-southeast1-docker.pkg.dev/$P/goats/goats-hsw-rag-chatbot:v3
for i in $(seq 1 $N); do
  echo "=== start test $i  $(date -u +%H:%M:%S)"
  gcloud run deploy $S --project $P --region $R --image $IMG --no-traffic --tag st$i \
    --memory 4Gi --cpu 2 --cpu-boost --min-instances 0 --max-instances 2 --concurrency 10 --timeout 300 --allow-unauthenticated \
    --set-env-vars GRADIO_ANALYTICS_ENABLED=False,NONCE=$i --set-secrets GROQ_API_KEY=GROQ_API_KEY:2 2>&1 | grep -E "^Service|revision \[" | cut -c1-160
  curl -s -o /dev/null -w "tag st$i GET / : %{http_code} in %{time_total}s\n" --max-time 200 https://st$i---goats-hsw-rag-chatbot-edc7oz3psq-as.a.run.app/
  curl -s -o /dev/null -w "tag st$i GET /config : %{http_code} in %{time_total}s\n" --max-time 60 https://st$i---goats-hsw-rag-chatbot-edc7oz3psq-as.a.run.app/config
done
echo "=== done $(date -u +%H:%M:%S)"
