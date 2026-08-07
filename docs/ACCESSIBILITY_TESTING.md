# Accessibility verification

The automated Chromium smoke test covers the assistant's keyboard focus entry,
Shift+Tab wrap, Escape dismissal, background inertness, focus return, language
selection, status changes, streaming chat, and failure recovery. The checks below
remain a human release gate because visual clarity and screen-reader quality
cannot be established by DOM assertions alone.

## Keyboard-only check

1. Open `/` in English, German, and Latvian.
2. Press Tab from the browser chrome through the skip link, navigation, language
   controls, PDF link, smart-home link, and chat launcher. Every interactive
   element must show a visible focus indicator.
3. Activate the skip link and confirm focus/scroll moves to the main content.
4. Activate each language button and confirm `aria-pressed` follows the visible
   language and the PDF target changes with it.
5. Open the CV assistant. Focus must move to the message input and background
   content must no longer receive focus.
6. Cycle forward and backward through the dialog. Focus must remain inside it.
7. Submit a message and confirm the busy state is exposed while the send button
   is disabled, then focus returns to the input after completion or failure.
8. Press Escape. The assistant must close and focus must return to its launcher.
9. Repeat at 320 CSS-pixel width and 200% browser zoom. No control, message, or
   privacy notice may be clipped or require horizontal page scrolling.

## Screen-reader check

Test at least one current desktop combination, such as Firefox with NVDA or
Safari with VoiceOver.

- The page has one main landmark and a meaningful heading hierarchy.
- Language controls announce their pressed state.
- The assistant announces a modal dialog with its title and description.
- The privacy notice is available before the first message is sent.
- Busy, completed, and error states are announced once without reading every
  streamed token individually.
- User and assistant messages retain an understandable reading order.
- Closing the dialog returns the virtual cursor/focus to the launcher.

## Visual and motion check

- Verify text and focus indicators meet WCAG AA contrast in normal, hover, focus,
  live, stale, offline, success, and error states.
- Enable the operating system's reduced-motion preference and confirm decorative
  transitions are removed or substantially reduced.
- Check touch targets on a phone-sized viewport; controls should remain at least
  44 by 44 CSS pixels where practical.
- Confirm content is usable with images disabled and that decorative images do
  not add noisy alternative text.

Record the browser, assistive technology, date, and any exception in the pull
request before a user-interface release is merged.
