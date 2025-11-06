"""
Playwright MCP를 사용하여 Lichess 분석 도구 열기
"""
import os
import asyncio
import re
from typing import Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"Warning: MCP library not available: {e}")
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

# 전역 MCP 세션 관리
_mcp_session: Optional[ClientSession] = None
_mcp_session_context = None
_mcp_read_write = None
_mcp_client_context = None
_mcp_initialized = False


async def initialize_mcp_session() -> bool:
    """
    MCP 세션을 초기화합니다 (애플리케이션 시작 시 한 번 호출)
    
    Returns:
        초기화 성공 여부
    """
    global _mcp_session, _mcp_session_context, _mcp_read_write, _mcp_client_context, _mcp_initialized
    
    if _mcp_initialized:
        return _mcp_session is not None
    
    _mcp_initialized = True
    
    # MCP 라이브러리 확인
    if ClientSession is None or stdio_client is None:
        print("MCP library not available, skipping MCP connection")
        return False
    
    mcp_command = os.getenv("MCP_SERVER_COMMAND", "npx")
    mcp_args_str = os.getenv("MCP_SERVER_ARGS", "-y @playwright/mcp")
    mcp_args = mcp_args_str.split() if mcp_args_str else []
    
    try:
        server_params = StdioServerParameters(
            command=mcp_command,
            args=mcp_args
        )
        
        _mcp_client_context = stdio_client(server_params)
        _mcp_read_write = await _mcp_client_context.__aenter__()
        read, write = _mcp_read_write
        
        _mcp_session_context = ClientSession(read, write)
        _mcp_session = await _mcp_session_context.__aenter__()
        
        await asyncio.sleep(0.5)
        try:
            await asyncio.wait_for(_mcp_session.initialize(), timeout=15.0)
            print("MCP session initialized successfully")
            return True
        except Exception as init_error:
            print(f"MCP session initialization failed: {init_error}")
            await cleanup_mcp_session()
            return False
    
    except Exception as e:
        print(f"Error initializing MCP session: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        await cleanup_mcp_session()
        return False


async def cleanup_mcp_session():
    """
    MCP 세션을 정리합니다 (애플리케이션 종료 시 호출)
    """
    global _mcp_session, _mcp_session_context, _mcp_read_write, _mcp_client_context, _mcp_initialized
    
    try:
        if _mcp_session and _mcp_session_context:
            try:
                await _mcp_session_context.__aexit__(None, None, None)
            except:
                pass
            _mcp_session = None
            _mcp_session_context = None
        
        if _mcp_read_write and _mcp_client_context:
            try:
                await _mcp_client_context.__aexit__(None, None, None)
            except:
                pass
            _mcp_read_write = None
            _mcp_client_context = None
        
        _mcp_initialized = False
        print("MCP session cleaned up")
    except Exception as e:
        print(f"Error cleaning up MCP session: {e}")


def get_mcp_session() -> Optional[ClientSession]:
    """
    전역 MCP 세션을 반환합니다
    
    Returns:
        MCP 세션 또는 None
    """
    return _mcp_session


async def open_lichess_analysis_with_playwright(game_id: str, ply: int, moves: list[str]) -> Optional[str]:
    """
    Playwright MCP를 사용하여 Lichess 분석 도구를 열고 현재 기보 상태 설정
    
    Args:
        game_id: 게임 ID
        ply: 현재 ply (0부터 시작)
        moves: ply까지의 수 목록 (SAN 형식)
    
    Returns:
        열린 브라우저의 URL 또는 None (실패 시)
    """
    # 전역 세션 사용
    session = get_mcp_session()
    if session is None:
        print("MCP session not available, attempting to initialize...")
        initialized = await initialize_mcp_session()
        if not initialized:
            print("Failed to initialize MCP session")
            return None
        session = get_mcp_session()
        if session is None:
            return None
    
    try:
        # FEN 생성
        import chess
        board = chess.Board()
        for i in range(ply):
            if i < len(moves):
                try:
                    move = board.parse_san(moves[i])
                    board.push(move)
                except:
                    continue
        
        fen = board.fen()
        # FEN을 URL 인코딩
        from urllib.parse import quote
        encoded_fen = quote(fen)
        
        # 사용 가능한 도구 목록 확인
        tools_result = await session.list_tools()
        available_tools = {tool.name for tool in tools_result.tools}
        
        # navigate 도구 찾기
        navigate_tool_name = None
        for tool_name in ["mcp_playwright_browser_navigate", "browser_navigate", "navigate"]:
            if tool_name in available_tools:
                navigate_tool_name = tool_name
                break
        
        if not navigate_tool_name:
            print(f"Navigate tool not found. Available tools: {list(available_tools)}")
            return None
                
        # 분석 도구로 이동
        analysis_url = "https://lichess.org/analysis"
        
        # 기존 탭 재사용 시도
        try:
            tabs_result = await session.call_tool(
                "mcp_playwright_browser_tabs",
                arguments={"action": "list"}
            )
            
            existing_tab = None
            if tabs_result:
                tabs_data = None
                if isinstance(tabs_result, dict):
                    tabs_data = tabs_result.get('content', [])
                elif hasattr(tabs_result, 'content'):
                    if isinstance(tabs_result.content, list):
                        tabs_data = tabs_result.content
                    elif isinstance(tabs_result.content, str):
                        try:
                            import json
                            tabs_data = json.loads(tabs_result.content)
                        except:
                            tabs_data = None
                
                if tabs_data:
                    for tab in tabs_data:
                        tab_url = None
                        tab_index = None
                        if isinstance(tab, dict):
                            tab_url = tab.get('url', '')
                            tab_index = tab.get('index', 0)
                        elif hasattr(tab, 'url'):
                            tab_url = tab.url
                            tab_index = getattr(tab, 'index', 0)
                        
                        if tab_url and 'lichess.org/analysis' in tab_url:
                            existing_tab = tab
                            break
            
            if existing_tab:
                tab_index = 0
                if isinstance(existing_tab, dict):
                    tab_index = existing_tab.get('index', 0)
                elif hasattr(existing_tab, 'index'):
                    tab_index = existing_tab.index
                
                print(f"Reusing existing tab {tab_index}")
                await session.call_tool(
                    "mcp_playwright_browser_tabs",
                    arguments={"action": "select", "index": tab_index}
                )
                await session.call_tool(
                    navigate_tool_name,
                    arguments={"url": analysis_url}
                )
            else:
                print("Opening new tab")
                await session.call_tool(
                    navigate_tool_name,
                    arguments={"url": analysis_url}
                )
        except Exception as tab_error:
            print(f"Tab management failed, opening new tab: {tab_error}")
            await session.call_tool(
                navigate_tool_name,
                arguments={"url": analysis_url}
            )
        
        # 페이지 로드 대기
        await asyncio.sleep(3)
        
        # 도구 확인
        evaluate_tool_name = None
        for tool_name in ["mcp_playwright_browser_evaluate", "browser_evaluate", "evaluate"]:
            if tool_name in available_tools:
                evaluate_tool_name = tool_name
                break
        
        # textarea 대기
        if evaluate_tool_name:
            textarea_ready = False
            for attempt in range(15):
                js_check = """() => {
                    const textarea = document.querySelector('textarea');
                    if (!textarea) return false;
                    const isVisible = textarea.offsetParent !== null;
                    const hasValue = textarea.value !== undefined;
                    return isVisible && hasValue;
                }"""
                try:
                    check_result = await session.call_tool(
                        evaluate_tool_name,
                        arguments={"function": js_check}
                    )
                    
                    result_text = None
                    if isinstance(check_result, dict):
                        result_text = str(check_result.get('content', ''))
                    elif hasattr(check_result, 'content'):
                        if isinstance(check_result.content, list):
                            result_text = str(check_result.content[0]) if check_result.content else ''
                        else:
                            result_text = str(check_result.content)
                    else:
                        result_text = str(check_result)
                    
                    if result_text and ('true' in result_text.lower() or result_text.strip() == 'true'):
                        textarea_ready = True
                        print(f"Textarea ready after {attempt + 1} attempts")
                        break
                except Exception as check_error:
                    print(f"Error checking textarea (attempt {attempt + 1}): {check_error}")
                
                await asyncio.sleep(1)
            
            if not textarea_ready:
                print("Warning: Textarea not found after waiting 15 seconds")
        
        # PGN 입력
        if moves and ply > 0 and evaluate_tool_name:
            try:
                from backend.lichess_api import fetch_game_data
                game_data = await fetch_game_data(game_id)
                full_pgn = game_data.pgn
                
                import chess
                import chess.pgn
                from io import StringIO
                
                pgn_io_full = StringIO(full_pgn)
                full_game = chess.pgn.read_game(pgn_io_full)
                
                if full_game:
                    new_game = chess.pgn.Game()
                    new_game.headers = full_game.headers.copy()
                    new_game.headers["Event"] = "Analysis"
                    
                    board_pgn = chess.Board()
                    node = new_game
                    move_count = 0
                    
                    for node_in_full in full_game.mainline():
                        if move_count >= ply:
                            break
                        move = node_in_full.move
                        if move in board_pgn.legal_moves:
                            board_pgn.push(move)
                            node = node.add_variation(move)
                            move_count += 1
                        else:
                            print(f"Warning: Illegal move at ply {move_count}: {move}")
                            break
                    
                    pgn_io = StringIO()
                    exporter = chess.pgn.FileExporter(pgn_io)
                    new_game.accept(exporter)
                    full_pgn_string = pgn_io.getvalue().strip()
                    
                    lines = full_pgn_string.split('\n')
                    move_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('['):
                            continue
                        move_lines.append(line)
                    
                    pgn_string = ' '.join(move_lines).strip()
                    pgn_string = re.sub(r'\s+[*\d\-/]+\s*$', '', pgn_string)
                    pgn_string = pgn_string.strip()
                else:
                    # 폴백: moves 배열로 생성
                    print("Warning: Failed to parse full PGN, falling back to moves array")
                    game = chess.pgn.Game()
                    game.headers["Event"] = "Analysis"
                    board_pgn = chess.Board()
                    node = game
                    
                    for i in range(min(ply, len(moves))):
                        try:
                            move_san = moves[i]
                            move = board_pgn.parse_san(move_san)
                            node = node.add_variation(move)
                            board_pgn.push(move)
                        except Exception as move_error:
                            print(f"Error adding move {i} to PGN: {move_error}")
                            continue
                    
                    pgn_io = StringIO()
                    exporter = chess.pgn.FileExporter(pgn_io)
                    game.accept(exporter)
                    full_pgn_string = pgn_io.getvalue().strip()
                    
                    lines = full_pgn_string.split('\n')
                    move_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('['):
                            continue
                        move_lines.append(line)
                    
                    pgn_string = ' '.join(move_lines).strip()
                    pgn_string = re.sub(r'\s+[*\d\-/]+\s*$', '', pgn_string)
                    pgn_string = pgn_string.strip()
                
                # PGN 입력
                import json
                pgn_escaped = json.dumps(pgn_string)
                
                print(f"Attempting to paste PGN (length: {len(pgn_string)})")
                
                js_pgn = f"""() => {{
                    const pgnText = {pgn_escaped};
                    const textarea = document.querySelector('textarea');
                    if (!textarea) return 'Textarea not found';
                    
                    textarea.focus();
                    textarea.select();
                    textarea.value = '';
                    textarea.value = pgnText;
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    const enterDown = new KeyboardEvent('keydown', {{ 
                        key: 'Enter', 
                        code: 'Enter', 
                        keyCode: 13, 
                        which: 13, 
                        bubbles: true, 
                        cancelable: true 
                    }});
                    const enterPress = new KeyboardEvent('keypress', {{ 
                        key: 'Enter', 
                        code: 'Enter', 
                        keyCode: 13, 
                        which: 13, 
                        bubbles: true, 
                        cancelable: true 
                    }});
                    const enterUp = new KeyboardEvent('keyup', {{ 
                        key: 'Enter', 
                        code: 'Enter', 
                        keyCode: 13, 
                        which: 13, 
                        bubbles: true, 
                        cancelable: true 
                    }});
                    
                    textarea.dispatchEvent(enterDown);
                    textarea.dispatchEvent(enterPress);
                    textarea.dispatchEvent(enterUp);
                    
                    const currentValue = textarea.value;
                    return 'PGN set: ' + currentValue.substring(0, 40) + ' (length: ' + currentValue.length + ')';
                }}"""
                
                pgn_result = await session.call_tool(
                    evaluate_tool_name,
                    arguments={"function": js_pgn}
                )
                
                # 결과에서 간단한 메시지만 추출
                result_summary = "Success"
                try:
                    if isinstance(pgn_result, dict):
                        content = pgn_result.get('content', '')
                        if isinstance(content, str):
                            # "### Result" 섹션에서 "PGN set:" 부분만 찾기
                            if '### Result' in content:
                                result_section = content.split('### Result')[1].split('###')[0] if '### Result' in content else content
                                if 'PGN set:' in result_section:
                                    result_summary = result_section.split('PGN set:')[1].split('\n')[0].strip()
                                elif 'Textarea not found' in result_section:
                                    result_summary = "Failed: Textarea not found"
                            elif 'PGN set:' in content:
                                result_summary = content.split('PGN set:')[1].split('\n')[0].strip()
                        elif isinstance(content, list):
                            # 리스트인 경우 첫 번째 항목 확인
                            for item in content:
                                item_str = str(item)
                                if 'PGN set:' in item_str:
                                    result_summary = item_str.split('PGN set:')[1].split('\n')[0].strip()
                                    break
                    elif hasattr(pgn_result, 'content'):
                        if isinstance(pgn_result.content, list):
                            for item in pgn_result.content:
                                item_str = str(item) if not isinstance(item, str) else item
                                if 'PGN set:' in item_str:
                                    # 마크다운 형식에서 Result 섹션만 추출
                                    if '### Result' in item_str:
                                        result_section = item_str.split('### Result')[1].split('###')[0]
                                        if 'PGN set:' in result_section:
                                            result_summary = result_section.split('PGN set:')[1].split('\n')[0].strip()
                                    else:
                                        result_summary = item_str.split('PGN set:')[1].split('\n')[0].strip()
                                    break
                        else:
                            content_str = str(pgn_result.content)
                            if '### Result' in content_str:
                                result_section = content_str.split('### Result')[1].split('###')[0]
                                if 'PGN set:' in result_section:
                                    result_summary = result_section.split('PGN set:')[1].split('\n')[0].strip()
                            elif 'PGN set:' in content_str:
                                result_summary = content_str.split('PGN set:')[1].split('\n')[0].strip()
                except Exception as parse_error:
                    # 파싱 실패 시 성공으로 간주 (도구 호출 자체는 성공했으므로)
                    result_summary = "Success"
                
                print(f"PGN paste: {result_summary}")
                await asyncio.sleep(3)
                
            except Exception as js_error:
                print(f"Error pasting PGN with JavaScript: {js_error}")
                import traceback
                traceback.print_exc()
        
        # 최종 URL 확인
        final_analysis_url = f"https://lichess.org/analysis?fen={encoded_fen}"
        
        try:
            await asyncio.sleep(1)
            tabs_result = await session.call_tool(
                "mcp_playwright_browser_tabs",
                arguments={"action": "list"}
            )
            if tabs_result:
                tabs_data = None
                if isinstance(tabs_result, dict):
                    tabs_data = tabs_result.get('content', [])
                elif hasattr(tabs_result, 'content'):
                    if isinstance(tabs_result.content, list):
                        tabs_data = tabs_result.content
                
                if tabs_data:
                    for tab in tabs_data:
                        tab_url = None
                        if isinstance(tab, dict):
                            if tab.get('current', False):
                                tab_url = tab.get('url', '')
                        elif hasattr(tab, 'current') and tab.current:
                            if hasattr(tab, 'url'):
                                tab_url = tab.url
                        
                        if tab_url and ('#' in tab_url or 'analysis' in tab_url):
                            final_analysis_url = tab_url
                            print(f"Found updated URL with PGN: {final_analysis_url}")
                            break
        except Exception as url_error:
            print(f"Warning: Could not get updated URL: {url_error}")
        
        print(f"Completed: PGN input finished")
        print(f"Final URL: {final_analysis_url}")
        
        return final_analysis_url
    
    except Exception as e:
        print(f"Error using MCP session: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def setup_lichess_board_via_playwright(game_id: str, ply: int, moves: list[str]) -> str:
    """
    FEN을 기반으로 Lichess 분석 도구 URL 생성
    
    Args:
        game_id: 게임 ID
        ply: 현재 ply
        moves: ply까지의 수 목록
    
    Returns:
        Lichess 분석 도구 URL
    """
    import chess
    from urllib.parse import quote
    
    # 현재 ply까지의 보드 상태를 FEN으로 변환
    board = chess.Board()
    for i in range(ply):
        if i < len(moves):
            try:
                move = board.parse_san(moves[i])
                board.push(move)
            except:
                continue
    
    fen = board.fen()
    
    # Lichess 분석 도구 URL 생성
    # Lichess는 fen 쿼리 파라미터를 지원함
    encoded_fen = quote(fen)
    analysis_url = f"https://lichess.org/analysis?fen={encoded_fen}"
    
    return analysis_url

