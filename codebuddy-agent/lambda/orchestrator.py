import json
import os
import hmac
import hashlib
import boto3
import requests

# 환경 변수
AGENT_ID = os.environ.get('AGENT_ID', '')
ALIAS_ID = os.environ.get('ALIAS_ID', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_SECRET = os.environ.get('GITHUB_SECRET', '')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='ap-northeast-2')


def verify_github_signature(payload_body: bytes, signature: str) -> bool:
    """GitHub Webhook 서명 검증"""
    if not GITHUB_SECRET:
        return True  # 개발 환경에서는 검증 생략
    expected = 'sha256=' + hmac.new(
        GITHUB_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def invoke_bedrock_agent(pr_url: str, session_id: str) -> str:
    """Bedrock Agent 호출"""
    prompt = f"""
다음 GitHub PR을 분석해주세요: {pr_url}

아래 항목을 순서대로 수행해주세요:
1. get_github_pr 툴로 PR 코드 가져오기
2. analyze_complexity 툴로 복잡도 분석
3. 보안 취약점 확인 (SQL Injection, 하드코딩된 비밀번호 등)
4. generate_unit_test 툴로 테스트 코드 제안
5. suggest_refactor 툴로 리팩토링 제안
6. post_pr_comment 툴로 GitHub PR에 리뷰 댓글 등록
7. send_slack 툴로 Slack에 알림 전송
"""

    response = bedrock_agent.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=ALIAS_ID,
        sessionId=session_id,
        inputText=prompt
    )

    result = ''
    for event in response['completion']:
        if 'chunk' in event:
            result += event['chunk']['bytes'].decode('utf-8')

    return result


def send_slack_notification(pr_url: str, status: str, summary: str):
    """Slack 알림 전송"""
    if not SLACK_WEBHOOK_URL:
        print("Slack Webhook URL이 설정되지 않았습니다.")
        return

    emoji = "✅" if status == "success" else "❌"
    message = {
        "text": f"{emoji} *CodeBuddy 리뷰 완료*\nPR: {pr_url}\n상태: {status}\n요약: {summary[:200]}..."
    }
    try:
        requests.post(SLACK_WEBHOOK_URL, json=message, timeout=5)
    except Exception as e:
        print(f"Slack 알림 전송 실패: {e}")


def handler(event, context):
    """Lambda 핸들러"""
    print(f"Event: {json.dumps(event)}")

    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    body = {}
    try:
        # OPTIONS 요청 처리 (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}

        # 1. Body 추출 및 None/Base64 인코딩 방어
        raw_body_str = event.get('body')
        if raw_body_str is None:
            raw_body_str = '{}'

        if event.get('isBase64Encoded', False):
            import base64
            raw_body_bytes = base64.b64decode(raw_body_str)
            raw_body_str = raw_body_bytes.decode('utf-8')
        else:
            raw_body_bytes = raw_body_str.encode('utf-8') if isinstance(raw_body_str, str) else b''

        # 2. JSON 안전 파싱 (실패 시 AttributeError/500 에러 대신 400 응답)
        try:
            body = json.loads(raw_body_str) if isinstance(raw_body_str, str) else raw_body_str
            if not isinstance(body, dict):
                body = {}
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '유효하지 않은 JSON 페이로드입니다.'}, ensure_ascii=False)
            }

        # 3. GitHub Webhook 서명 검증 (정확한 원본 바이트 페이로드 사용)
        signature = event.get('headers', {}).get('X-Hub-Signature-256', '')
        if signature and not verify_github_signature(raw_body_bytes, signature):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid signature'})
            }

        # 4. PR URL 추출 (직접 호출 또는 Webhook 분기 처리 안전성 강화)
        pr_url = body.get('pr_url')
        if not pr_url:
            # GitHub Webhook 형식 파싱
            pull_request = body.get('pull_request', {})
            pr_url = pull_request.get('html_url')
            action = body.get('action', '')

            # PR이 열리거나 변경되었을 때만 처리
            if action not in ['opened', 'synchronize']:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({'message': f'Action {action} ignored'})
                }

        if not pr_url:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'pr_url이 필요합니다'}, ensure_ascii=False)
            }

        # PR 번호로 세션 ID 생성
        pr_number = pr_url.split('/')[-1]
        session_id = f"webhook-{pr_number}"

        print(f"PR 분석 시작: {pr_url}")

        # Bedrock Agent 호출
        result = invoke_bedrock_agent(pr_url, session_id)

        # Slack 알림
        send_slack_notification(pr_url, "success", result)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'PR 리뷰 완료',
                'pr_url': pr_url,
                'result': result
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"오류 발생: {e}")
        send_slack_notification(
            body.get('pr_url', 'unknown') if isinstance(body, dict) else 'unknown',
            "error",
            str(e)
        )
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }