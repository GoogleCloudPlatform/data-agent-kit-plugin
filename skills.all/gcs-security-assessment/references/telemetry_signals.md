# Telemetry Signals Reference

These are the signals you gather during Phase 1. For each signal, the source
tells you which sub-skill or tool to use. If a signal is unavailable, log the
gap and move on.

## Object-Level Signals

| Signal                  | Source     | What to Check                       |
| ----------------------- | ---------- | ----------------------------------- |
| Public access           | BQ Dataset | Whether the object is publicly      |
:                         :            : accessible                          :
| Object versioning       | BQ Dataset | Whether previous versions are       |
:                         :            : retained on overwrite/delete        :
| RetentionExpirationTime | BQ Dataset | Whether a retention policy prevents |
:                         :            : premature deletion                  :
| Encryption type         | BQ Dataset | GMEK (Google-default), CMEK         |
:                         :            : (customer-managed), or CSEK         :
:                         :            : (customer-supplied)                 :

## Bucket-Level Signals

| Signal                   | Source     | What to Check                        |
| ------------------------ | ---------- | ------------------------------------ |
| Enforced encryption type | BQ Dataset | Whether an encryption type is        |
: allowed                  :            : enforced for the bucket              :
| UBLA configuration       | BQ Dataset | Whether Uniform Bucket-Level Access  |
:                          :            : is enabled                           :
| Soft delete policy       | BQ Dataset | Whether deleted objects are retained |
:                          :            : for a recovery window, and the       :
:                          :            : duration                             :

## Project-Level Signals

| Signal                | Source              | What to Check                |
| --------------------- | ------------------- | ---------------------------- |
| IAM over-permissions  | IAM Policy + IAM    | Whether any principals have  |
:                       : Recommender API     : broader roles than needed    :
:                       :                     : (e.g., `roles/storage.admin` :
:                       :                     : when                         :
:                       :                     : `roles/storage.objectViewer` :
:                       :                     : suffices)                    :
| VPC Service Controls  | Access Context      | Whether the project is       |
:                       : Manager API         : inside a VPC-SC perimeter    :
| Cloud Audit Logging   | Cloud Resource      | Whether DATA_READ and        |
: (Data Access)         : Manager API         : DATA_WRITE audit logs are    :
:                       :                     : enabled for                  :
:                       :                     : `storage.googleapis.com`     :
| Data residency org    | Org Policy API      | Whether org policies         |
: policy                :                     : constrain resource locations :
:                       :                     : to specific regions          :
| Block HTTP org policy | Org Policy API      | Whether plaintext HTTP       |
:                       :                     : traffic is blocked           :
| TLS org policy        | Org Policy API      | Whether minimum TLS version  |
:                       :                     : is restricted to 1.2+        :
| HMAC org policy       | Org Policy API      | Whether HMAC authentication  |
:                       :                     : is restricted via            :
:                       :                     : `storage.restrictAuthTypes`  :
| Model Armor API       | Model Armor API     | Whether                      |
: status                :                     : `modelarmor.googleapis.com`  :
:                       :                     : is enabled                   :
| Model Armor floor     | `gcloud model-armor | Whether minimum security     |
: settings              : floorsettings`      : thresholds are configured    :
| Model Armor templates | `gcloud model-armor | Whether any screening        |
:                       : templates list`     : templates exist              :
| Model Armor Vertex AI | Model Armor floor   | Whether Model Armor is       |
: integration           : settings API        : activated for Vertex AI      :
:                       :                     : Gemini calls                 :
