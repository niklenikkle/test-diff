from pexpect.popen_spawn import PopenSpawn
import sys
import time

git_bash = r'C:\Program Files\Git\bin\bash.exe'
project_dir = '/d/aipro/ai07'

try:
    print("启动 Git Bash...")
    child = PopenSpawn(git_bash + ' --login -i', timeout=30, encoding='utf-8')
    
    print("等待提示符...")
    child.expect(r'\$', timeout=10)
    time.sleep(0.5)
    
    print(f"切换到目录: {project_dir}")
    child.sendline(f'cd {project_dir}')
    child.expect(r'\$', timeout=5)
    time.sleep(0.5)
    
    print("启动 Claude Code...")
    child.sendline('claude')
    
    print("等待 Claude 响应...")
    time.sleep(3)
    
    child.sendline('')
    time.sleep(2)
    
    print("\n读取输出...")
    try:
        output = child.read_nonblocking(size=10000, timeout=2)
        print("=== 输出开始 ===")
        print(output)
        print("=== 输出结束 ===")
    except:
        print("无更多输出")
    
except Exception as e:
    print(f"❌ 错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
