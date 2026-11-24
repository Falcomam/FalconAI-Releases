"""Falcon's per-reply copy affordance for its existing Tkinter chat.

A user click copies *only* the unmodified reply string from the corresponding
Falcon chat message. No new windows, permission changes or model interaction.
"""
from __future__ import annotations

_COPY_LABEL = "  ⧉ Copy reply\n"


def copy_reply_to_clipboard(root, original_reply):
    """Copy exact original Unicode reply text, not chat transcript decorations."""
    if not isinstance(original_reply, str):
        raise TypeError("Falcon reply must be literal text")
    root.clipboard_clear()
    root.clipboard_append(original_reply)
    # Make clipboard contents available even if the GUI is minimized/closed.
    root.update_idletasks()


def attach_copy_reply(widget, root, original_reply, *, accent="#a884ff",
                      success="#69e6bc", on_error=None):
    """Append a clickable copy link to a single Falcon message on the same Text widget.

    Bindings are unique for each message; later messages can never overwrite a
    previous link's clipboard payload. The widget must be temporarily editable
    as part of the existing Falcon.append method.
    """
    if not isinstance(original_reply, str):
        raise TypeError("Falcon reply must be literal text")
    sequence = getattr(widget, "_falcon_copy_sequence", 0) + 1
    setattr(widget, "_falcon_copy_sequence", sequence)
    tag = f"falcon_copy_reply_{sequence}"

    widget.insert("end", _COPY_LABEL, (tag,))
    widget.tag_configure(tag, foreground=accent, underline=True)

    def handle_click(_event=None):
        try:
            copy_reply_to_clipboard(root, original_reply)
        except Exception as exc:
            if on_error is not None:
                on_error(str(exc)[:160])
            return "break"
        try:
            widget.tag_configure(tag, foreground=success)
            root.after(1100, lambda: _restore_color(widget, tag, accent))
        except Exception:
            pass
        return "break"

    def handle_enter(_event=None):
        try:
            widget.configure(cursor="hand2")
        except Exception:
            pass

    def handle_leave(_event=None):
        try:
            widget.configure(cursor="xterm")
        except Exception:
            pass

    widget.tag_bind(tag, "<Button-1>", handle_click)
    widget.tag_bind(tag, "<Enter>", handle_enter)
    widget.tag_bind(tag, "<Leave>", handle_leave)
    return tag


def _restore_color(widget, tag, accent):
    try:
        widget.tag_configure(tag, foreground=accent)
    except Exception:
        # The chat may have been cleared or the app closed.
        pass
