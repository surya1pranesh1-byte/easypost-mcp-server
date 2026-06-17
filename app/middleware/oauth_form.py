from __future__ import annotations

import html


def render_oauth_form(
    *,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> str:
    def e(text: str | None) -> str:
        return html.escape(text or "", quote=True)

    error_html = f'<div class="error">{e(error)}</div>' if error else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EasyPost MCP OAuth</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .container {{
      background: white;
      border-radius: 8px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      max-width: 420px;
      width: 100%;
      padding: 40px;
    }}
    .header {{ margin-bottom: 30px; }}
    .header h1 {{ font-size: 24px; font-weight: 600; color: #333; margin-bottom: 8px; }}
    .header p {{ font-size: 14px; color: #666; line-height: 1.5; }}
    .form-group {{ margin-bottom: 20px; }}
    label {{ display: block; font-size: 14px; font-weight: 500; color: #333; margin-bottom: 8px; }}
    input[type="password"] {{
      width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px;
      font-size: 14px; font-family: monospace; transition: border-color 0.2s;
    }}
    input[type="password"]:focus {{ outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }}
    .error {{
      background: #fee; border: 1px solid #fcc; border-radius: 4px;
      padding: 12px; margin-bottom: 20px; color: #c33; font-size: 14px;
    }}
    .submit-btn {{
      width: 100%; padding: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white; border: none; border-radius: 4px;
      font-size: 14px; font-weight: 600; cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .submit-btn:hover {{ transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.3); }}
    .help-text {{ font-size: 12px; color: #999; margin-top: 20px; line-height: 1.5; }}
    .help-text a {{ color: #667eea; text-decoration: none; }}
    .help-text a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>EasyPost API Authorization</h1>
      <p>Please enter your EasyPost API key to authorize this application.</p>
    </div>
    {error_html}
    <form method="POST">
      <input type="hidden" name="client_id" value="{e(client_id)}">
      <input type="hidden" name="redirect_uri" value="{e(redirect_uri)}">
      <input type="hidden" name="state" value="{e(state)}">
      <div class="form-group">
        <label for="api_key">EasyPost API Key</label>
        <input type="password" id="api_key" name="api_key"
          placeholder="EZTK... (test) or EZAK... (production)"
          required autofocus autocomplete="off">
      </div>
      <button type="submit" class="submit-btn">Authorize</button>
      <div class="help-text">
        <strong>Don't have an API key?</strong><br>
        <a href="https://www.easypost.com/signup" target="_blank">Create a free EasyPost account</a> to get started.<br><br>
        <strong>Security:</strong> Your API key is validated in real-time but never stored permanently.
      </div>
    </form>
  </div>
</body>
</html>"""
