import httpx
import re
import os
import asyncio
from typing import List, Optional, Tuple
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
backend_dir = Path(__file__).parent
env_file = backend_dir.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# 프로젝트 루트를 Python 경로에 추가
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from backend.models import GameData, Player, CloudEval


LICHESS_API_BASE = "https://lichess.org/api"
LICHESS_API_TOKEN = os.getenv("LICHESS_API_TOKEN", "")


def get_auth_headers() -> dict:
    """인증 헤더 반환 (토큰이 있는 경우)"""
    headers = {}
    if LICHESS_API_TOKEN:
        headers["Authorization"] = f"Bearer {LICHESS_API_TOKEN}"
    return headers


def extract_game_id(game_url: str) -> str:
    """Lichess 게임 URL에서 게임 ID 추출
    
    Lichess 게임 ID는 보통 8자리입니다. URL에 추가 경로(/black, /white 등)가 있을 수 있습니다.
    게임 ID는 대소문자를 구분합니다.
    """
    # URL에서 공백 제거
    game_url = game_url.strip()
    
    # 제외할 경로 목록
    excluded_paths = ['game', 'export', 'api', 'study', 'training', 'black', 'white', 'analysis']
    
    # 1. /game/export/{gameId} 형식 먼저 확인
    match = re.search(r'/game/export/([a-zA-Z0-9]{4,20})', game_url)
    if match:
        game_id = match.group(1)
        if game_id not in excluded_paths:
            return game_id
    
    # 2. https://lichess.org/{gameId} 형식 (가장 일반적)
    # 게임 ID는 보통 8자리이며, 그 뒤에 /black, /white, /analysis 등이 올 수 있음
    # 12자리 게임 ID도 가능하지만, 8자리 패턴을 우선 확인
    match = re.search(r'lichess\.org/([a-zA-Z0-9]{8})(?:/|$|Z)', game_url)
    if match:
        game_id = match.group(1)
        if game_id not in excluded_paths:
            return game_id
    
    # 2-1. 12자리 게임 ID 시도
    match = re.search(r'lichess\.org/([a-zA-Z0-9]{12})(?:/|$)', game_url)
    if match:
        game_id = match.group(1)
        if game_id not in excluded_paths:
            return game_id
    
    # 2-2. 4-20자 범위 (fallback)
    match = re.search(r'lichess\.org/([a-zA-Z0-9]{4,20})(?:/|$)', game_url)
    if match:
        game_id = match.group(1)
        # 경로 제외 및 유효성 체크
        if game_id not in excluded_paths and 4 <= len(game_id) <= 20:
            return game_id
    
    # 3. URL에서 숫자/문자 조합 찾기 (더 포괄적)
    match = re.search(r'lichess\.org/([a-zA-Z0-9]+)', game_url)
    if match:
        game_id = match.group(1)
        # 경로 제외 및 최소 길이 체크
        if game_id not in excluded_paths and 4 <= len(game_id) <= 20:
            return game_id
    
    # 전체 URL이 아닌 경우 (게임 ID만 입력된 경우)
    if re.match(r'^[a-zA-Z0-9]{4,20}$', game_url):
        return game_url
    
    raise ValueError(
        f"Invalid Lichess game URL or ID: {game_url}\n"
        "올바른 형식: https://lichess.org/ABC12345 또는 https://lichess.org/ABC123456789\n"
        f"입력된 값: '{game_url}'\n"
        "참고: URL에 /black, /white 등의 경로가 있을 수 있지만, 게임 ID만 추출됩니다."
    )


async def fetch_game_data(game_id: str) -> GameData:
    """Lichess API로 게임 데이터 가져오기
    토큰이 있으면 비공개 게임도 접근 가능합니다.
    PGN에서 모든 정보를 추출합니다.
    """
    headers = get_auth_headers()
    has_token = bool(LICHESS_API_TOKEN)
    
    # Lichess PGN 내보내기 엔드포인트: GET https://lichess.org/game/export/{gameId}
    # 주의: 이 엔드포인트는 /api 접두사 없이 직접 호출합니다
    # 여러 URL 시도 (쿼리 파라미터 포함)
    pgn_urls = [
        f"https://lichess.org/game/export/{game_id}",
        f"https://lichess.org/game/export/{game_id}?evals=0&clocks=0",  # 폴백
        f"https://lichess.org/game/export/{game_id}?literate=1",
    ]
    pgn_url = pgn_urls[0]  # 기본 URL
    pgn = None  # PGN 변수를 함수 레벨에서 초기화
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 여러 PGN URL 시도 (첫 번째 URL 성공하면 바로 종료)
            pgn_response = None
            max_retries = 2  # 3 → 2로 감소
            for url in pgn_urls:
                print(f"Fetching game from: {url}")
                
                # 재시도 로직 (빠른 실패)
                for attempt in range(max_retries):
                    try:
                        response = await client.get(
                            url,
                            headers=headers,
                            timeout=15.0,  # 30초 → 15초로 감소 (더 빠른 응답)
                            follow_redirects=True
                        )
                        if response.status_code == 200:
                            pgn_response = response
                            pgn_url = url
                            break
                        elif response.status_code == 403:
                            # IP 차단 가능성
                            raise ValueError("Lichess에서 IP가 차단된 것으로 보입니다. VPN을 사용하거나 잠시 후 다시 시도해주세요.")
                    except (httpx.ConnectTimeout, httpx.ConnectError) as e:
                        if attempt < max_retries - 1:
                            wait_time = 1.0  # 2초 → 1초로 감소
                            print(f"Connection timeout/error (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # 다음 URL로 시도 (마지막 URL이 아니면)
                            if url != pgn_urls[-1]:
                                print(f"Failed to fetch from {url}, trying next URL...")
                                break
                            raise ValueError(
                                f"Lichess 사이트에 연결할 수 없습니다. 네트워크 연결을 확인하거나 VPN을 사용해주세요. "
                                f"(에러: {type(e).__name__})"
                            )
                    except Exception as e:
                        if url != pgn_urls[-1]:
                            print(f"Error with {url}, trying next URL...")
                            break
                        raise
                
                if pgn_response and pgn_response.status_code == 200:
                    break
            
            if pgn_response and pgn_response.status_code == 200:
                pgn = pgn_response.text
                print(f"Successfully fetched PGN (length: {len(pgn)})")
                
                if not pgn or len(pgn.strip()) == 0:
                    raise ValueError(f"Empty PGN response for game: {game_id}")
                    
            elif pgn_response.status_code == 404:
                # 게임 페이지가 존재하는지 먼저 확인
                game_page_url = f"https://lichess.org/{game_id}"
                game_exists = False
                try:
                    print(f"Checking if game page exists: {game_page_url}")
                    page_check = await client.get(game_page_url, timeout=5.0, follow_redirects=True)
                    game_exists = page_check.status_code == 200
                    print(f"Game page check result: status={page_check.status_code}, exists={game_exists}")
                except Exception as page_error:
                    print(f"Error checking game page: {page_error}")
                    game_exists = False
                
                if game_exists:
                    # 게임 페이지에서 직접 PGN을 추출 시도 (fallback)
                    print("Attempting to extract game data from HTML page...")
                    try:
                        html_content = page_check.text
                        # Lichess 게임 페이지에서 PGN을 찾기 위해 여러 방법 시도
                        
                        import json
                        import html as html_module
                        pgn_from_html = None
                        
                        # 방법 1: HTML에서 직접 PGN 텍스트 추출 (페이지에 표시된 PGN)
                        # Lichess는 PGN을 텍스트로 페이지에 표시합니다
                        pgn_patterns = [
                            # PGN 섹션에서 직접 추출: [Event "..." 부터 시작하는 패턴
                            r'\[Event\s+"[^"]+"\][^\[]*\[Site\s+"[^"]+"\][^\[]*\[Date\s+"[^"]+"\][^\[]*\[White\s+"[^"]+"\][^\[]*\[Black\s+"[^"]+"\][^\[]*\[Result\s+"[^"]+"\][^"]*1\.\s+[^\]]+',
                            # data-pgn 속성이나 data-game 속성 찾기
                            r'data-pgn="([^"]+)"',
                            r'data-pgn=\'([^\']+)\'',
                            # generic 태그 내 PGN 텍스트 (Lichess가 PGN을 generic 태그로 표시)
                            r'<generic[^>]*>\[Event\s+"[^"]+"\][^<]+</generic>',
                            r'"pgn"\s*:\s*"([^"]+)"',
                            r'"pgn"\s*:\s*\'([^\']+)\'',
                            r'pgn["\']\s*:\s*["\']([^"\']+)["\']',
                        ]
                        
                        for pattern in pgn_patterns:
                            matches = re.finditer(pattern, html_content, re.IGNORECASE | re.MULTILINE)
                            for match in matches:
                                try:
                                    pgn_candidate = match.group(1)
                                    # HTML 엔티티 디코딩
                                    pgn_candidate = html_module.unescape(pgn_candidate)
                                    # PGN 형식인지 확인 (태그가 있는지)
                                    if '[Event' in pgn_candidate or '[White' in pgn_candidate:
                                        pgn_from_html = pgn_candidate
                                        print(f"Found PGN in HTML using pattern: {pattern[:30]}...")
                                        break
                                except:
                                    continue
                            if pgn_from_html:
                                break
                        
                        # 방법 2: script 태그에서 게임 데이터 찾기 (JSON 형식)
                        if not pgn_from_html:
                            script_patterns = [
                                r'<script[^>]*>.*?lichess.*?initStore.*?game.*?</script>',
                                r'<script[^>]*>.*?lichess\.round.*?pgn.*?</script>',
                                r'lichess\.round\.init\([^)]+\)',
                            ]
                            
                            for script_pattern in script_patterns:
                                scripts = re.findall(script_pattern, html_content, re.DOTALL | re.IGNORECASE)
                                for script in scripts:
                                    # JSON 데이터에서 pgn 찾기
                                    json_patterns = [
                                        r'"pgn"\s*:\s*"([^"]+)"',
                                        r'"pgn"\s*:\s*\'([^\']+)\'',
                                    ]
                                    for json_pattern in json_patterns:
                                        match = re.search(json_pattern, script, re.IGNORECASE)
                                        if match:
                                            try:
                                                pgn_candidate = match.group(1)
                                                pgn_candidate = html_module.unescape(pgn_candidate)
                                                if '[Event' in pgn_candidate or '[White' in pgn_candidate:
                                                    pgn_from_html = pgn_candidate
                                                    print(f"Found PGN in script tag")
                                                    break
                                            except:
                                                continue
                                if pgn_from_html:
                                    break
                        
                        # 방법 3: /api/game/ 엔드포인트에서 JSON으로 게임 데이터 가져오기
                        if not pgn_from_html:
                            try:
                                # moves를 포함한 JSON 가져오기 시도
                                json_urls = [
                                    f"{LICHESS_API_BASE}/game/{game_id}?moves=1",
                                    f"{LICHESS_API_BASE}/game/{game_id}?withMoves=1",
                                    f"{LICHESS_API_BASE}/game/{game_id}",
                                ]
                                
                                game_json = None
                                for json_url in json_urls:
                                    print(f"Attempting to fetch game JSON from: {json_url}")
                                    json_response = await client.get(json_url, headers=headers, timeout=5.0)
                                    print(f"JSON API response status: {json_response.status_code}")
                                    if json_response.status_code == 200:
                                        game_json = json_response.json()
                                        print(f"JSON keys: {list(game_json.keys())}")
                                        # moves가 있으면 이 URL 사용
                                        if 'moves' in game_json:
                                            print(f"Found 'moves' key in this JSON response")
                                            break
                                    elif json_response.status_code == 404:
                                        print(f"JSON API returned 404 for {json_url}")
                                    else:
                                        print(f"JSON API returned status {json_response.status_code}")
                                
                                # moves가 없는 경우, 게임 페이지에서 직접 게임 데이터 추출 시도
                                if game_json and 'moves' not in game_json:
                                    print("JSON doesn't contain 'moves', trying to extract from game page HTML...")
                                    # 게임 페이지 HTML을 다시 확인하여 moves 추출
                                    # Lichess는 보통 게임 데이터를 JavaScript 변수나 데이터 속성에 저장
                                    try:
                                        # 더 포괄적인 패턴으로 moves 찾기
                                        # 1. JavaScript 객체에서 moves 찾기
                                        # 먼저 script 태그에서 모든 JavaScript 코드 추출
                                        # 여러 패턴 시도 (type 속성이 있거나 없는 경우)
                                        script_patterns = [
                                            r'<script[^>]*>(.*?)</script>',
                                            r'<script[^>]*type=["\']text/javascript["\'][^>]*>(.*?)</script>',
                                            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                                        ]
                                        all_scripts = []
                                        for pattern in script_patterns:
                                            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                                            all_scripts.extend(matches)
                                        
                                        script_text = '\n'.join(all_scripts)
                                        print(f"Extracted {len(all_scripts)} script tags, total length: {len(script_text)}")
                                        
                                                        # 디버깅: script 태그 내용의 일부 출력
                                        if script_text:
                                            print(f"Script content preview (first 500 chars): {script_text[:500]}")
                                        
                                        # 디버깅: HTML에서 "lichess" 또는 "game" 관련 내용 찾기
                                        lichess_refs = re.findall(r'lichess[^"\'<>\s]{0,50}', html_content, re.IGNORECASE)
                                        if lichess_refs:
                                            print(f"Found {len(lichess_refs)} 'lichess' references (first 5): {lichess_refs[:5]}")
                                        
                                        # 여러 패턴으로 moves 찾기
                                        moves_patterns = [
                                            # 가장 일반적인 패턴: "moves":"e2e4 e7e5 ..."
                                            r'["\']moves["\']\s*:\s*["\']([a-h][0-9][a-h][0-9][qrbn]?(?:\s+[a-h][0-9][a-h][0-9][qrbn]?)+)["\']',
                                            # lichess.round.data에서 찾기
                                            r'lichess\.round\.data\s*=\s*(\{[^}]+"moves"[^}]+"([^"]+)"[^}]*\})',
                                            # data 속성
                                            r'data-moves=["\']([^"\']+)["\']',
                                            # JSON 객체 내 moves
                                            r'"moves"\s*:\s*"([^"]+)"',
                                            # JavaScript 변수 할당
                                            r'moves\s*=\s*["\']([^"\']+)["\']',
                                        ]
                                        
                                        # script 태그 내용에서 먼저 검색
                                        search_text = script_text if script_text else html_content
                                        
                                        for pattern in moves_patterns:
                                            matches = re.finditer(pattern, search_text, re.DOTALL | re.IGNORECASE)
                                            for match in matches:
                                                try:
                                                    moves_str = match.group(1)
                                                    print(f"Found potential moves string (length: {len(moves_str)}): {moves_str[:100]}")
                                                    
                                                    # JSON 파싱 시도
                                                    if moves_str.strip().startswith('{'):
                                                        import json
                                                        moves_json = json.loads(moves_str)
                                                        if isinstance(moves_json, dict) and 'moves' in moves_json:
                                                            moves_data = moves_json['moves']
                                                            if isinstance(moves_data, str):
                                                                moves_data = moves_data.split()
                                                        else:
                                                            continue
                                                    elif moves_str.strip().startswith('['):
                                                        import json
                                                        moves_data = json.loads(moves_str)
                                                        if isinstance(moves_data, list):
                                                            pass  # 이미 리스트
                                                        else:
                                                            continue
                                                    else:
                                                        # 공백으로 구분된 UCI 이동 문자열
                                                        moves_data = moves_str.split()
                                                    
                                                    # UCI 형식인지 확인 (예: "e2e4", "g1f3")
                                                    valid_moves = []
                                                    for m in moves_data[:10]:  # 처음 10개만 확인
                                                        if isinstance(m, str) and len(m) >= 4 and m[0].islower() and m[1].isdigit():
                                                            valid_moves.append(m)
                                                    
                                                    if len(valid_moves) >= 2:  # 최소 2개 이상의 유효한 이동
                                                        print(f"Found {len(moves_data)} valid moves in HTML")
                                                        game_json['moves'] = moves_data
                                                        break
                                                except Exception as parse_error:
                                                    print(f"Error parsing moves from pattern: {parse_error}")
                                                    continue
                                            if 'moves' in game_json:
                                                break
                                    except Exception as html_extract_error:
                                        print(f"Error extracting moves from HTML: {html_extract_error}")
                                        import traceback
                                        traceback.print_exc()
                                
                                if game_json:
                                    # JSON에서 PGN 추출
                                    if 'pgn' in game_json:
                                        pgn_from_json = game_json['pgn']
                                        print(f"Found 'pgn' key in JSON, length: {len(pgn_from_json) if isinstance(pgn_from_json, str) else 'not a string'}")
                                        if isinstance(pgn_from_json, str) and ('[Event' in pgn_from_json or '[White' in pgn_from_json):
                                            pgn_from_html = pgn_from_json
                                            print(f"Successfully extracted PGN from JSON API response")
                                    # 또는 moves 배열/문자열에서 PGN 재구성 시도
                                    if not pgn_from_html and 'moves' in game_json:
                                        # moves는 문자열(공백 구분)이거나 리스트일 수 있음
                                        moves_data = game_json['moves']
                                        print(f"Found 'moves' key in JSON, type: {type(moves_data).__name__}, value preview: {str(moves_data)[:100] if moves_data else 'None'}")
                                        if moves_data and (isinstance(moves_data, str) or isinstance(moves_data, list)):
                                            print(f"Found moves in JSON ({type(moves_data).__name__}), attempting to reconstruct PGN...")
                                            try:
                                                reconstructed_pgn = reconstruct_pgn_from_json(game_json, game_id)
                                                if reconstructed_pgn:
                                                    pgn_from_html = reconstructed_pgn
                                                    print(f"Successfully reconstructed PGN from JSON moves (length: {len(reconstructed_pgn)})")
                                                else:
                                                    print("PGN reconstruction returned None")
                                            except Exception as recon_error:
                                                print(f"Error reconstructing PGN: {recon_error}")
                                                import traceback
                                                traceback.print_exc()
                            except Exception as json_error:
                                print(f"Error fetching JSON game data: {json_error}")
                                import traceback
                                traceback.print_exc()
                        
                        # 방법 4: 게임 페이지에서 PGN 다운로드 링크 찾기
                        if not pgn_from_html:
                            print("Searching for PGN download links in HTML...")
                            # PGN 다운로드 링크 패턴 찾기
                            download_patterns = [
                                r'href=["\']([^"\']*\.pgn[^"\']*)["\']',
                                r'href=["\']([^"\']*export[^"\']*pgn[^"\']*)["\']',
                                r'href=["\']([^"\']*download[^"\']*pgn[^"\']*)["\']',
                                r'data-url=["\']([^"\']*pgn[^"\']*)["\']',
                            ]
                            for pattern in download_patterns:
                                matches = re.finditer(pattern, html_content, re.IGNORECASE)
                                for match in matches:
                                    url = match.group(1)
                                    if url.startswith('/'):
                                        url = f"https://lichess.org{url}"
                                    elif not url.startswith('http'):
                                        url = f"https://lichess.org/{url}"
                                    
                                    if 'pgn' in url.lower() or 'export' in url.lower():
                                        print(f"Found potential PGN download URL: {url}")
                                        try:
                                            dl_response = await client.get(url, headers=headers, timeout=5.0)
                                            if dl_response.status_code == 200:
                                                content = dl_response.text
                                                if '[Event' in content or '[White' in content:
                                                    pgn_from_html = content
                                                    print(f"Successfully downloaded PGN from: {url}")
                                                    break
                                        except:
                                            continue
                                if pgn_from_html:
                                    break
                        
                        # 방법 5: 다른 PGN 엔드포인트 시도
                        if not pgn_from_html:
                            alternative_urls = [
                                f"https://lichess.org/game/export/{game_id}?format=pgn",
                                f"https://lichess.org/{game_id}.pgn",
                                f"https://lichess.org/game/{game_id}/pgn",
                            ]
                            for alt_url in alternative_urls:
                                try:
                                    alt_response = await client.get(alt_url, headers=headers, timeout=5.0)
                                    if alt_response.status_code == 200:
                                        content = alt_response.text
                                        # PGN 형식인지 확인 (PGN은 일반적으로 [로 시작하는 태그를 포함)
                                        if content.strip().startswith('[') or '[Event' in content[:500] or '[White' in content[:500]:
                                            pgn_from_html = content
                                            print(f"Successfully fetched PGN from alternative endpoint: {alt_url}")
                                            print(f"PGN preview (first 300 chars): {content[:300]}")
                                            break
                                        else:
                                            print(f"Response from {alt_url} doesn't look like PGN (first 200 chars): {content[:200]}")
                                except Exception as alt_error:
                                    print(f"Error fetching from {alt_url}: {alt_error}")
                                    continue
                        
                        if pgn_from_html and len(pgn_from_html.strip()) > 0:
                            # PGN을 찾았으므로 계속 진행
                            print("Successfully extracted PGN from HTML/alternative endpoint")
                            pgn = pgn_from_html
                        else:
                            # PGN을 찾지 못함 - 에러 발생
                            raise ValueError("Could not extract PGN from game page")
                            
                    except ValueError as extract_error:
                        # PGN 추출 실패 - 에러 메시지 표시
                        print(f"Failed to extract PGN from HTML: {extract_error}")
                        
                        # 최종 시도: 게임 페이지의 모든 링크에서 export/pgn 관련 링크 찾기
                        print("Final attempt: Searching for any export/download links in HTML...")
                        all_links = re.findall(r'href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                        export_links = [link for link in all_links if any(kw in link.lower() for kw in ['export', 'pgn', 'download'])]
                        if export_links:
                            print(f"Found {len(export_links)} potential export links: {export_links[:5]}")
                        
                        error_msg = (
                            f"게임 PGN을 가져올 수 없습니다: {game_id}\n"
                            f"\n시도한 방법:\n"
                            f"1. /game/export/{game_id} 엔드포인트 (404)\n"
                            f"2. HTML에서 PGN 데이터 추출 (실패)\n"
                            f"3. JSON API에서 moves 데이터 추출 (moves 필드 없음)\n"
                            f"4. 대체 PGN 엔드포인트 (모두 실패)\n"
                            f"\n가능한 원인:\n"
                            f"- 게임이 비공개로 설정되어 있습니다\n"
                            f"- 게임이 아직 진행 중이거나 공개되지 않았습니다\n"
                            f"- 게임이 Study나 Training 게임일 수 있습니다\n"
                            f"- 이 게임 ID 형식이 API에서 지원되지 않을 수 있습니다\n"
                            f"\n게임 확인: https://lichess.org/{game_id}"
                        )
                        if has_token:
                            error_msg += "\n\nAPI 토큰이 설정되어 있지만, 토큰의 소유자가 이 게임의 참여자인지 확인해주세요."
                        else:
                            error_msg += "\n\n비공개 게임인 경우 API 토큰이 필요할 수 있습니다. .env 파일에 LICHESS_API_TOKEN을 설정해보세요."
                        
                        error_msg += "\n\n다른 공개 게임 URL로 테스트해보세요."
                        raise ValueError(error_msg)
                    except Exception as extract_error:
                        # 다른 예외는 그대로 전달
                        raise
                    
                    # PGN을 성공적으로 추출했으면, pgn 변수가 설정되었으므로 계속 진행 (에러 발생하지 않음)
                else:
                    error_msg = (
                        f"Game not found: {game_id}.\n"
                        f"게임이 존재하지 않습니다.\n"
                        f"게임 ID는 대소문자를 구분하므로 확인해주세요: https://lichess.org/{game_id}"
                    )
                    raise ValueError(error_msg)
                    
            elif pgn_response.status_code == 403:
                raise ValueError(
                    f"Access forbidden: {game_id}. "
                    "이 게임에 대한 접근 권한이 없습니다. "
                    f"{'토큰이 올바른지 확인해주세요.' if has_token else 'API 토큰이 필요할 수 있습니다.'}"
                )
            else:
                pgn_response.raise_for_status()
                pgn = pgn_response.text
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                error_msg = (
                    f"Game not found: {game_id}.\n"
                    f"게임이 존재하지 않거나 접근 권한이 없습니다.\n"
                    f"게임 ID는 대소문자를 구분하므로 확인해주세요: https://lichess.org/{game_id}"
                )
                if has_token:
                    error_msg += "\n토큰의 소유자와 게임 참여자가 일치하는지 확인해주세요."
                else:
                    error_msg += "\n비공개 게임은 API 토큰이 필요합니다."
                raise ValueError(error_msg)
            elif e.response.status_code == 403:
                raise ValueError(
                    f"Access forbidden: {game_id}. "
                    f"{'토큰이 올바른지 확인해주세요.' if has_token else 'API 토큰이 필요할 수 있습니다.'}"
                )
            raise
    
    final_game_id = game_id  # 이미 8자리로 추출되었음
    
    # PGN 내용 확인 (디버깅)
    print(f"PGN content length: {len(pgn) if pgn else 0}")
    if pgn:
        print(f"PGN preview (first 500 chars):\n{pgn[:500]}")
        print(f"PGN preview (last 200 chars):\n{pgn[-200:]}")
    
    # PGN 파싱하여 메타데이터 추출
    moves = parse_pgn_moves(pgn)
    print(f"Parsed {len(moves)} moves from PGN")
    
    # PGN 헤더에서 정보 추출
    white_name = "Unknown"
    black_name = "Unknown"
    white_rating = None
    black_rating = None
    opening = None
    result = "*"
    
    # PGN 태그 파싱
    pgn_lines = pgn.split('\n')
    for line in pgn_lines:
        line = line.strip()
        if line.startswith('[White '):
            match = re.search(r'\[White "([^"]+)"\]', line)
            if match:
                white_name = match.group(1)
        elif line.startswith('[Black '):
            match = re.search(r'\[Black "([^"]+)"\]', line)
            if match:
                black_name = match.group(1)
        elif line.startswith('[WhiteElo '):
            match = re.search(r'\[WhiteElo "([^"]+)"\]', line)
            if match:
                try:
                    white_rating = int(match.group(1)) if match.group(1) != '?' else None
                except ValueError:
                    pass
        elif line.startswith('[BlackElo '):
            match = re.search(r'\[BlackElo "([^"]+)"\]', line)
            if match:
                try:
                    black_rating = int(match.group(1)) if match.group(1) != '?' else None
                except ValueError:
                    pass
        elif line.startswith('[Opening '):
            match = re.search(r'\[Opening "([^"]+)"\]', line)
            if match:
                opening = match.group(1)
        elif line.startswith('[Result '):
            match = re.search(r'\[Result "([^"]+)"\]', line)
            if match:
                result_str = match.group(1)
                if result_str == "1-0":
                    result = "white"
                elif result_str == "0-1":
                    result = "black"
                elif result_str == "1/2-1/2":
                    result = "draw"
                else:
                    result = "*"
    
    white = Player(username=white_name, rating=white_rating)
    black = Player(username=black_name, rating=black_rating)
    
    return GameData(
        game_id=final_game_id,  # 실제로 작동한 게임 ID 사용
        white=white,
        black=black,
        pgn=pgn,
        opening=opening,
        result=result,
        moves=moves
    )


def reconstruct_pgn_from_json(game_json: dict, game_id: str) -> str:
    """Lichess JSON API 응답에서 PGN 재구성"""
    import chess
    import chess.pgn
    
    try:
        # 게임 정보 추출
        white_name = game_json.get('players', {}).get('white', {}).get('user', {}).get('name', 'Unknown')
        black_name = game_json.get('players', {}).get('black', {}).get('user', {}).get('name', 'Unknown')
        white_rating = game_json.get('players', {}).get('white', {}).get('rating')
        black_rating = game_json.get('players', {}).get('black', {}).get('rating')
        opening = game_json.get('opening', {}).get('name')
        result = game_json.get('winner')  # 'white', 'black', None
        if result == 'white':
            result_str = "1-0"
        elif result == 'black':
            result_str = "0-1"
        else:
            result_str = "1/2-1/2"  # draw or ongoing
        
        # moves 배열/문자열에서 게임 재구성
        moves_data = game_json.get('moves', '')
        if isinstance(moves_data, str):
            # 공백으로 구분된 UCI 이동 문자열
            moves_list = moves_data.split() if moves_data.strip() else []
        elif isinstance(moves_data, list):
            moves_list = moves_data
        else:
            print(f"Moves data is neither string nor list: {type(moves_data)}")
            return None
        
        if not moves_list:
            print("No moves found in JSON")
            return None
        
        # python-chess로 게임 재구성
        game = chess.pgn.Game()
        game.headers["Event"] = "Lichess Game"
        game.headers["Site"] = f"https://lichess.org/{game_id}"
        game.headers["White"] = white_name
        game.headers["Black"] = black_name
        if white_rating:
            game.headers["WhiteElo"] = str(white_rating)
        if black_rating:
            game.headers["BlackElo"] = str(black_rating)
        if opening:
            game.headers["Opening"] = opening
        game.headers["Result"] = result_str
        
        # 보드 생성하고 이동 적용
        node = game
        board = chess.Board()
        
        for move_uci in moves_list:
            try:
                move = chess.Move.from_uci(move_uci)
                if move in board.legal_moves:
                    # SAN 변환
                    san_move = board.san(move)
                    board.push(move)
                    # 다음 노드로 이동
                    node = node.add_variation(move, comment=None)
                else:
                    print(f"Invalid move: {move_uci}")
                    break
            except Exception as e:
                print(f"Error parsing move {move_uci}: {e}")
                break
        
        # PGN 문자열 생성
        from io import StringIO
        pgn_io = StringIO()
        exporter = chess.pgn.FileExporter(pgn_io)
        game.accept(exporter)
        pgn_string = pgn_io.getvalue()
        return pgn_string
        
    except Exception as e:
        print(f"Error reconstructing PGN from JSON: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_pgn_moves(pgn: str) -> List[str]:
    """PGN에서 SAN 이동 추출 (주석 제거)"""
    # PGN 형식: 1. e4 {[%eval 0.2]} e5 {[%eval -0.1]} ...
    moves = []
    
    # PGN에서 이동 부분만 추출 (태그 뒤의 실제 이동)
    # 태그는 [로 시작하고 ]로 끝나는 줄
    move_text = ""
    for line in pgn.split('\n'):
        line = line.strip()
        if line and not line.startswith('['):
            # 태그가 아닌 줄이면 이동 텍스트
            move_text += " " + line
    
    move_text = move_text.strip()
    
    # 중괄호로 둘러싸인 주석 제거 (예: {[%eval 0.2]}, {[%clk 0:01:30]})
    # 중첩된 중괄호도 처리
    move_text = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', move_text)
    
    # [로 시작하는 주석도 제거 (예: [%eval ...])
    move_text = re.sub(r'\[[^\]]*\]', '', move_text)
    
    # python-chess를 사용하여 더 정확하게 파싱
    try:
        import chess.pgn
        from io import StringIO
        pgn_io = StringIO(pgn)
        game = chess.pgn.read_game(pgn_io)
        
        if game:
            board = game.board()
            for node in game.mainline():
                move = node.move
                # SAN 변환 (현재 보드 상태 기반)
                san_move = board.san(move)
                moves.append(san_move)
                board.push(move)
            return moves
    except Exception as e:
        print(f"Warning: python-chess PGN parsing failed, falling back to regex: {e}")
        import traceback
        traceback.print_exc()
        # 폴백: 정규식 파싱
    
    # 이동 패턴 매칭: 숫자. 이동1 이동2 형식
    # 예: "1. e4 e5 2. Nf3" -> ["e4", "e5", "Nf3"]
    pattern = r'\d+\.\s+(.*?)(?=\s*\d+\.|$)'
    matches = re.findall(pattern, move_text)
    
    for match in matches:
        # 각 이동 쌍을 개별 이동으로 분리
        # 예: "e4 e5" -> ["e4", "e5"]
        parts = match.strip().split()
        for part in parts:
            # 결과 기호(1-0, 0-1, 1/2-1/2) 제거
            if part in ["1-0", "0-1", "1/2-1/2", "*"]:
                continue
            # 체크메이트 기호(#)가 있는 경우 제거
            part = part.rstrip('#+')
            # 빈 문자열, 주석 관련 문자열 제거
            if (part and 
                not part.startswith('[') and 
                not part.startswith('{') and 
                not part.startswith('}') and
                not part.startswith('%') and
                '[' not in part and
                '{' not in part):
                # 유효한 체스 이동인지 간단히 확인
                # SAN 형식: 알파벳으로 시작하거나 O-O (캐슬링)
                if (part and 
                    (part[0].isalpha() or 
                     part.startswith('O-O') or
                     part[0].isupper())):
                    moves.append(part)
    
    return moves


async def fetch_cloud_eval(fen: str, depth: int = 15, max_retries: int = 2) -> CloudEval:
    """Lichess Cloud Eval API로 위치 평가 가져오기"""
    url = f"{LICHESS_API_BASE}/cloud-eval"
    headers = get_auth_headers()
    has_token = bool(LICHESS_API_TOKEN)
    
    # FEN을 URL 인코딩 (httpx가 자동으로 처리하지만 명시적으로)
    # FEN 형식: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    params = {
        "fen": fen,  # httpx가 자동으로 URL 인코딩함
    }
    # depth와 multiPv는 선택적 파라미터 (API가 자동으로 처리)
    if depth:
        params["depth"] = depth
    
    # API 토큰이 있으면 더 짧은 타임아웃과 빠른 재시도
    timeout = 15.0 if has_token else 30.0
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 404:
                    # 404인 경우 - 이 위치에 대한 평가가 아직 준비되지 않음 (정상적인 경우)
                    # Lichess Cloud Eval은 모든 위치를 즉시 평가하지 않음
                    raise ValueError(f"Cloud eval not available for this position (404) - position may not be evaluated yet")
                elif response.status_code == 429:
                    # Rate limit - 재시도 (토큰 있으면 더 짧게 대기)
                    if attempt < max_retries - 1:
                        wait_time = (0.5 * (attempt + 1)) if has_token else (2 ** attempt + 1)
                        # 처음 몇 번만 로그 출력 (너무 많은 로그 방지)
                        if attempt < 2:
                            print(f"Rate limit (429) hit, waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f"Rate limit exceeded (429) after {max_retries} attempts")
                
                response.raise_for_status()
                data = response.json()
                break  # 성공
        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue
            raise
    
    if last_error and 'data' not in locals():
        # 모든 재시도 실패
        raise ValueError(f"Failed to fetch cloud eval after {max_retries} attempts: {last_error}")
    
    # 응답 형식에 따라 파싱
    # 실제 API 응답: {"fen":"...", "knodes":105848192, "depth":70, "pvs":[{"moves":"e7e5 g1f3...", "cp":18}]}
    # knodes는 kilo-nodes (1000으로 곱해야 함)
    pvs_data = data.get("pvs", [{}])[0]
    
    # moves 필드 확인 (문자열로 오는 경우가 많음)
    pv_data = pvs_data.get("moves") or pvs_data.get("pv", [])
    
    if isinstance(pv_data, str):
        # 문자열인 경우 공백으로 분리
        pv = pv_data.split() if pv_data.strip() else []
    elif isinstance(pv_data, list):
        pv = pv_data
    else:
        pv = []
    
    # knodes를 nodes로 변환 (없으면 0)
    knodes = data.get("knodes", 0)
    nodes = int(knodes * 1000) if knodes else 0
    
    return CloudEval(
        fen=data.get("fen", fen),  # 응답에 fen이 포함되어 있을 수 있음
        cp=pvs_data.get("cp"),
        mate=pvs_data.get("mate"),
        depth=data.get("depth", depth),
        nodes=nodes,
        pv=pv
    )

