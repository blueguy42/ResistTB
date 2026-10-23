#!/usr/bin/env bash
# GCP environment for the analysis side. Run from a machine with gcloud and project owner access.
# Every command passes --project explicitly so the active gcloud config is never changed.
set -euo pipefail

PROJECT=haduh-512512
REGION=asia-southeast1          # bucket location
VM_ZONE=us-east4-a              # VM next to NCBI's US servers; Singapore downloads stalled
BUCKET=gs://${PROJECT}-genohack
SA_NAME=genohack-vm
SA=${SA_NAME}@${PROJECT}.iam.gserviceaccount.com
VM=genohack-analysis-us

gcloud services enable compute.googleapis.com storage.googleapis.com \
    billingbudgets.googleapis.com --project "${PROJECT}"

gcloud storage buckets create "${BUCKET}" --project "${PROJECT}" --location "${REGION}" \
    --uniform-bucket-level-access

gcloud iam service-accounts create "${SA_NAME}" --project "${PROJECT}" \
    --display-name "genohack analysis VM"
gcloud storage buckets add-iam-policy-binding "${BUCKET}" \
    --member "serviceAccount:${SA}" --role roles/storage.objectAdmin

# New projects may have no default network.
if ! gcloud compute networks describe default --project "${PROJECT}" >/dev/null 2>&1; then
    gcloud compute networks create default --project "${PROJECT}" --subnet-mode auto
fi
# SSH only from Google's IAP range, so no public SSH port is exposed.
gcloud compute firewall-rules create allow-iap-ssh --project "${PROJECT}" --network default \
    --direction INGRESS --allow tcp:22 --source-ranges 35.235.240.0/20 || true

gcloud compute instances create "${VM}" --project "${PROJECT}" --zone "${VM_ZONE}" \
    --machine-type e2-standard-8 \
    --image-family debian-12 --image-project debian-cloud \
    --boot-disk-size 400GB --boot-disk-type pd-balanced \
    --service-account "${SA}" --scopes cloud-platform \
    --labels project=genohack

# Connect: gcloud compute ssh ${VM} --zone ${VM_ZONE} --project ${PROJECT} --tunnel-through-iap
