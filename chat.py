"""Interactive terminal chat with local Qwen3.5-4B GPU model."""
import sys
from openai import OpenAI

def main():
    print("=" * 60)
    print("  🤖 Qwen3.5-4B Local Chat (CUDA GPU Accelerated)")
    print("  Gõ câu hỏi của bạn và nhấn Enter.")
    print("  Gõ 'exit' hoặc 'quit' để thoát.")
    print("=" * 60 + "\n")

    client = OpenAI(base_url="http://127.0.0.1:8005/v1", api_key="local-llama")
    history = [
        {"role": "system", "content": "You are a helpful, witty, and intelligent AI assistant. You can chat in Vietnamese and English naturally."}
    ]

    while True:
        try:
            user_input = input("\n👤 Bạn: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nTạm biệt! Chúc bạn một ngày tốt lành! 👋\n")
                break

            history.append({"role": "user", "content": user_input})

            print("\n🤖 Qwen: ", end="", flush=True)
            stream = client.chat.completions.create(
                model="qwen",
                messages=history,
                temperature=0.7,
                max_tokens=1000,
                stream=True,
            )

            assistant_response = ""
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content or ""
                    # Strip reasoning tags if model emits them
                    delta_clean = delta.replace("<think>", "").replace("</think>", "")
                    sys.stdout.write(delta_clean)
                    sys.stdout.flush()
                    assistant_response += delta_clean

            print()
            history.append({"role": "assistant", "content": assistant_response})

        except KeyboardInterrupt:
            print("\n\nĐã dừng chat. 👋\n")
            break
        except Exception as exc:
            print(f"\n[Lỗi kết nối: {exc}]")
            print("Hãy đảm bảo llama-server đang chạy tại http://127.0.0.1:8005/")
            break

if __name__ == "__main__":
    main()
