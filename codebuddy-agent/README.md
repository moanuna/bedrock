# 🤖 CodeBuddy Agent

**Amazon Bedrock 기반 GitHub PR 자동 리뷰 시스템**

GitHub에 PR이 열리면 AI Agent가 자동으로 코드를 분석하고 리뷰 댓글을 등록합니다.

---

## 🏗️ 아키텍처

```
GitHub PR 생성 (Webhook)
        ↓
API Gateway (POST /review) + API Key + Rate Limiting
        ↓
Orchestrator Lambda
  1. PR URL 파싱 → owner, repo, pr_number
  2. Bedrock Agent 호출 (sessionId=webhook-{pr})
  3. 결과 반환
        ↓
Bedrock Agent (CodeBuddy)
  - Instructions: 코드 리뷰 전문가
  - Knowledge Base: PEP8, OWASP
  - Action Group: 6개 Tools
        ↓
┌──────────────────────────────────────┐
│  get_github_pr   post_pr_comment  send_slack  │
│  analyze_complexity  generate_unit_test  suggest_refactor  │
└──────────────────────────────────────┘
```

---

## 🚀 빠른 시작

### 사전 요구사항

- AWS 계정 (ap-northeast-2 리전)
- Amazon Bedrock - Claude 모델 접근 권한
- GitHub Personal Access Token (repo 권한)
- Slack Incoming Webhook URL (선택)

### 1단계: CloudFormation으로 인프라 배포

```bash
aws cloudformation deploy \
  --template-file cloudformation/template.yaml \
  --stack-name CodeBuddyStack \
  --parameter-overrides \
    AgentIdParam=your-agent-id \
    AliasIdParam=your-alias-id \
    GitHubTokenParam=github_pat_xxx \
    GitHubSecretParam=your-webhook-secret \
    SlackWebhookUrlParam=https://hooks.slack.com/... \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-2
```

### 2단계: Bedrock Agent 생성

AWS 콘솔에서:

1. Amazon Bedrock → Agents → Create Agent
2. **이름**: CodeBuddy
3. **모델**: Claude 3.5 Sonnet (ap-northeast-2)
4. **Instructions** 아래 내용 붙여넣기:

```
당신은 시니어 소프트웨어 엔지니어로서 GitHub PR을 자동으로 리뷰합니다.
PR이 주어지면 다음 순서로 분석하세요:

1. get_github_pr 툴로 변경된 코드를 가져옵니다
2. 각 파일에 대해 analyze_complexity 툴로 복잡도와 보안 취약점을 분석합니다
3. generate_unit_test 툴로 테스트 코드를 생성합니다
4. suggest_refactor 툴로 리팩토링 제안을 생성합니다
5. post_pr_comment 툴로 분석 결과를 PR 댓글로 등록합니다
6. send_slack 툴로 팀에 알림을 전송합니다

리뷰는 친절하고 구체적으로 작성하며, 문제점과 함께 반드시 개선 방법을 제시합니다.
```

5. **Action Group** 추가:
   - Action Group 이름: CodeBuddyTools
   - Lambda: `codebuddy-tool-get-github-pr` 외 5개 Lambda 등록
   - API Schema: `docs/api-spec.yaml` 업로드

6. Agent 저장 후 **Prepare** → **Create Alias**

### 3단계: GitHub Webhook 설정

1. GitHub Repository → Settings → Webhooks → Add webhook
2. Payload URL: CloudFormation Output의 `ApiGatewayUrl`
3. Content type: `application/json`
4. Secret: CloudFormation 파라미터로 설정한 `GitHubSecretParam`
5. Events: **Pull requests** 선택

### 4단계: Lambda에 실제 코드 배포

```bash
# 각 툴 Lambda에 코드 배포
cd lambda
zip -r orchestrator.zip orchestrator.py
aws lambda update-function-code \
  --function-name codebuddy-orchestrator \
  --zip-file fileb://orchestrator.zip \
  --region ap-northeast-2

# tools 배포
cd tools
for tool in github_pr complexity testgen refactor post_comment send_slack; do
  zip ${tool}.zip ${tool}.py
  aws lambda update-function-code \
    --function-name codebuddy-tool-${tool//_/-} \
    --zip-file fileb://${tool}.zip \
    --region ap-northeast-2
done
```

---

## 📁 프로젝트 구조

```
codebuddy-agent/
├── README.md
├── cloudformation/
│   └── template.yaml          # 인프라 IaC (1클릭 배포)
├── lambda/
│   ├── orchestrator.py        # Webhook 수신 → Bedrock Agent 호출
│   └── tools/
│       ├── github_pr.py       # Tool 1: PR 코드 가져오기
│       ├── complexity.py      # Tool 2: 복잡도 & 보안 분석
│       ├── testgen.py         # Tool 3: 테스트 코드 생성
│       ├── refactor.py        # Tool 4: 리팩토링 제안
│       ├── post_comment.py    # Tool 5: GitHub PR 댓글 등록
│       └── send_slack.py      # Tool 6: Slack 알림
├── tests/
│   └── test_e2e.py            # E2E 테스트
├── docs/
│   └── api-spec.yaml          # OpenAPI 스키마 (Bedrock Agent용)
└── demo/
    └── demo.mp4               # 시연 영상
```

---

## 🔧 주요 기능

| 기능                | 설명                                          |
| ------------------- | --------------------------------------------- |
| 🔍 코드 스타일 검사 | PEP8 기준 (줄 길이, 네이밍, 들여쓰기)         |
| 🔒 보안 취약점 탐지 | SQL Injection, 하드코딩된 비밀번호, eval() 등 |
| 📊 복잡도 분석      | Cyclomatic Complexity 계산 및 위험 수준 평가  |
| 🧪 테스트 코드 생성 | pytest 기반 정상/비정상/Mock 테스트 자동 생성 |
| 🔧 리팩토링 제안    | 긴 함수, 중복 코드, 매직 넘버 탐지            |
| 📢 Slack 알림       | 리뷰 완료 시 팀 채널에 자동 알림              |

---

## 💰 월간 예상 비용 (서울 리전, 하루 100회 기준)

| 서비스                 | 월 비용     |
| ---------------------- | ----------- |
| Lambda (1024MB, 300초) | $11.00      |
| API Gateway            | $0.07       |
| Bedrock (Claude 3.5)   | $4.40       |
| CloudWatch Logs        | $1.10       |
| **합계**               | **~$16.57** |

---

## 🐛 트러블슈팅

| 오류                  | 원인            | 해결 방법                                  |
| --------------------- | --------------- | ------------------------------------------ |
| Agent 호출 403        | IAM 권한 부족   | `bedrock:InvokeAgent` 정책 확인            |
| Lambda timeout        | Agent 응답 지연 | timeout을 300초로 설정                     |
| Webhook 검증 실패     | Secret 불일치   | GitHub Secret과 Lambda 환경 변수 일치 확인 |
| GitHub API rate limit | 토큰 한도 초과  | Personal Access Token 권한 확인            |

---

## 📝 라이선스

MIT License

---

_CodeBuddy - AWS Generative AI 실무 10장 통합 프로젝트_
