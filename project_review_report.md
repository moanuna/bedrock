# 코드 리뷰 리포트

## 검사 대상
- 파일명: `FormBoard.js`
- 총 라인 수: 200줄

---

## 스타일 검사 결과

Airbnb JavaScript 스타일 가이드 기준으로 해당 코드의 문제점은 다음과 같습니다:

**1. `var` 대신 `const`/`let` 사용 (Variables)**
- 코드 자체에서 `var`는 사용되지 않았지만, 재할당되지 않는 변수들(`tagMap`, `payload`, `accessToken`, `response`)은 모두 `const`로 선언되어 있어야 합니다. 이 부분은 잘 지켜지고 있습니다.

**2. Trailing Comma 누락 (Objects)**
- `payload` 객체와 `tagMap` 객체의 마지막 프로퍼티에 trailing comma가 없습니다.
  ```js
  // 잘못된 예
  const payload = {
    fileUrls,
    imageUrls  // ← trailing comma 없음
  };

  // 올바른 예
  const payload = {
    fileUrls,
    imageUrls,
  };
  ```
- `tagMap` 객체의 `"기타": "OTHER"` 뒤에도 trailing comma가 없습니다.

**3. 함수 표현식 (Named Function Expressions)**
- `handleUpload`, `handleCloseModal` 등의 함수는 화살표 함수로 선언되어 있는데, Airbnb 가이드는 **named function expressions** 사용을 권장합니다.
  ```js
  // 권장
  const handleUpload = async function handleUpload() { ... };
  ```

**4. 불필요한 trailing whitespace / 주석 스타일**
- 인라인 주석(`// ← 이런 주석`) 뒤에 불필요한 공백이 있는 곳이 있습니다 (`setIsModalOpen(true); ` 등).

**요약**

| 문제 | 위치 |
|------|------|
| Trailing comma 누락 | `tagMap`, `payload` 객체 |
| Named function expression 미사용 | `handleUpload`, `handleCloseModal` 등 |
| 불필요한 trailing whitespace | 일부 주석 라인 |

---

## 보안 검사 결과

해당 코드에서 발견된 OWASP Top 10 기준 보안 취약점은 다음과 같습니다:

---

## A02 - Cryptographic Failures (암호화 실패)
- **JWT 토큰을 `sessionStorage`에 저장**하고 있습니다.
- `sessionStorage`는 JavaScript로 접근 가능하기 때문에 XSS 공격에 노출될 경우 토큰이 탈취될 수 있습니다.
- **권장 조치:** JWT 토큰은 `httpOnly` 쿠키에 저장해야 합니다.

---

## A03 - Injection (인젝션)
- `title`과 `details` 입력값에 대한 **유효성 검사(Validation)나 Sanitize 처리가 없습니다.**
- 사용자가 악성 스크립트나 쿼리를 입력할 경우, 서버 측에서 Injection 공격으로 이어질 수 있습니다.
- **권장 조치:** 입력값 유효성 검사 및 서버 측 파라미터 바인딩 적용이 필요합니다.

---

## A07 - Identification and Authentication Failures (인증 실패)
- `sessionStorage`에 토큰이 없을 경우 **`alert()`만 띄우고 이후 동작을 막지 않습니다.**
- 토큰 없이도 `handleUpload()`가 실행될 가능성이 있어, 인증되지 않은 요청이 발생할 수 있습니다.
- **권장 조치:** 토큰이 없을 경우 즉시 함수 실행을 중단하거나 로그인 페이지로 리다이렉트 해야 합니다.

---

## A09 - Security Logging and Monitoring Failures (보안 로깅 실패)
- `console.log("Payload being sent:", payload)` 및 `console.log("Response data:", response.data)` 등을 통해 **민감한 데이터가 브라우저 콘솔에 노출**됩니다.
- 특히 에러 핸들러에서 서버 응답 헤더, 상태 코드, 데이터 등을 모두 콘솔에 출력하고 있어 공격자에게 유용한 정보를 제공할 수 있습니다.
- **권장 조치:** 프로덕션 환경에서는 민감한 정보를 `console.log`로 출력하지 않아야 합니다.

---

## A05 - Security Misconfiguration (보안 설정 오류)
- `apiEndpoint`가 props로 외부에서 주입되며, **URL 검증 없이 그대로 axios 요청에 사용**됩니다.
- 악의적인 URL이 주입될 경우, 의도치 않은 서버로 민감 데이터가 전송될 수 있습니다.
- **권장 조치:** API 엔드포인트는 환경변수(`.env`)로 관리하고, 외부 URL 검증 로직을 추가해야 합니다.

