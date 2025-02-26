import markdown

text = "![Pasted image](/forum/api/image/1)"
html = markdown.markdown(text, extensions=['extra'])
print(html)  # Should output <img src="/forum/api/image/1" alt="Pasted image">
