# GitHub 업로드 가이드

## 1단계: GitHub에서 저장소 생성

1. https://github.com 에 로그인 (ldk4527@hs.ac.kr 계정)
2. 우측 상단의 **+** 버튼 클릭 → **New repository** 선택
3. 저장소 설정:
   - **Repository name**: `lichess_analyzer` (또는 원하는 이름)
   - **Description**: "Lichess Replay Analyzer with Playwright MCP"
   - **Visibility**: Public 또는 Private 선택
   - **⚠️ 중요**: 아래 옵션들은 모두 **체크하지 않기**:
     - ❌ **Add a README file** (이미 로컬에 README.md가 있음)
     - ❌ **Add .gitignore** (이미 로컬에 .gitignore가 있음)
     - ❌ **Choose a license** (필요시 나중에 추가 가능)
   
   > **왜 체크하지 않나요?**  
   > 이미 로컬에 커밋된 파일들이 있기 때문에, GitHub에서 자동으로 생성된 파일들과 충돌이 발생할 수 있습니다.  
   > 로컬 파일을 우선으로 사용하므로 이 옵션들은 비워두는 것이 안전합니다.

4. **Create repository** 클릭

## 2단계: 원격 저장소 연결 및 푸시

GitHub에서 저장소를 생성한 후, 아래 명령어를 실행하세요:

```bash
# 원격 저장소 추가 (YOUR_USERNAME을 실제 GitHub 사용자명으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/lichess_analyzer.git

# 기본 브랜치를 main으로 변경 (GitHub 기본값)
git branch -M main

# GitHub에 푸시
git push -u origin main
```

또는 SSH를 사용하는 경우:

```bash
git remote add origin git@github.com:YOUR_USERNAME/lichess_analyzer.git
git branch -M main
git push -u origin main
```

## 참고사항

- 저장소 이름이 다르다면 위 명령어의 `lichess_analyzer` 부분을 변경하세요
- GitHub에서 저장소를 생성하면 표시되는 URL을 사용하세요
- 인증이 필요할 수 있습니다 (Personal Access Token 또는 SSH 키)

