# SAIF Risk Factors

The
[Secure AI Framework (SAIF)](https://saif.google/secure-ai-framework/saif-map)
identifies 15 AI risks. The following subset is relevant to the telemetry
signals this skill can gather. Reference these risk names in your findings.

| SAIF Risk               | Description             | Indicating Signals (When |
:                         :                         : Misconfigured/Absent)    :
| ----------------------- | ----------------------- | ------------------------ |
| Unauthorized Training   | Data used for training  | UBLA disabled, public    |
: Data                    : that was not authorized : access enabled, IAM      :
:                         : for that purpose        : over-permissions, no     :
:                         :                         : audit logging            :
| Data Poisoning          | Malicious modification  | No object versioning, no |
:                         : of training or          : soft delete, IAM         :
:                         : evaluation data to      : over-permissions, no     :
:                         : corrupt model behavior  : audit logging            :
| Sensitive Data          | Model or system exposes | Public access enabled,   |
: Disclosure              : PII, financial, or      : no CMEK, no VPC-SC, no   :
:                         : other sensitive         : Model Armor, IAM         :
:                         : information             : over-permissions         :
| Model Exfiltration      | Unauthorized copying or | No VPC-SC, IAM           |
:                         : theft of model weights, : over-permissions, no     :
:                         : checkpoints, or         : audit logging            :
:                         : artifacts               :                          :
| Model Source Tampering  | Unauthorized            | No object versioning, no |
:                         : modification of model   : soft delete, no CMEK,    :
:                         : files, code, or         : IAM over-permissions, no :
:                         : dependencies            : audit logging            :
| Prompt Injection        | Adversarial inputs      | No Model Armor           |
:                         : designed to manipulate  : templates, no Vertex AI  :
:                         : model behavior or       : integration, no floor    :
:                         : bypass safety controls  : settings configured      :
| Insecure Model Output   | Model generates         | No Model Armor           |
:                         : harmful, biased, or     : templates, no Vertex AI  :
:                         : sensitive content       : integration              :
:                         : passed to users or      :                          :
:                         : downstream systems      :                          :
| Rogue Actions           | AI agent performs       | IAM over-permissions     |
:                         : unauthorized actions on : (agent service account), :
:                         : user data or systems    : no Model Armor, no audit :
:                         :                         : logging, no VPC-SC       :
| Denial of ML Service    | Attacks that degrade or | Public access enabled,   |
:                         : disrupt AI service      : no VPC-SC                :
:                         : availability            :                          :
| Excessive Data Handling | User data stored,       | No audit logging, no     |
:                         : processed, or retained  : data residency org       :
:                         : beyond what consent     : policy                   :
:                         : allows                  :                          :
