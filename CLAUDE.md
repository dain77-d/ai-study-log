# 작성 규칙

## 수식 (GitHub 렌더링)

GitHub는 수식을 MathJax에 넘기기 전에 Markdown 이스케이프를 먼저 처리한다. 그래서 `\{`, `\}`는 `{`, `}`로 바뀌고, `\Big\{`는 "Missing or unrecognized delimiter for \Big" 오류가 난다. `\{x\}`는 오류 없이 중괄호만 사라진다.

- 수식 안의 중괄호 기호는 `\{` `\}` 대신 항상 `\lbrace` `\rbrace`를 쓴다. 예: `\Big\lbrace ... \Big\rbrace`, `\mathbb 1_{\lbrace c\neq\varnothing\rbrace}`
- 커밋 전 `.github/workflows/math-lint.yml`과 같은 검사를 로컬에서 돌린다: `grep -rnF '\{' --include='*.md' . ; grep -rnF '\}' --include='*.md' .` 결과가 비어 있어야 한다.
