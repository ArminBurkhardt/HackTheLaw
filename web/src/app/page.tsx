"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChatTranscript } from "@/components/ai/ChatTranscript";
import { Composer } from "@/components/voice/Composer";
import { ErrorNotice } from "@/components/voice/ErrorNotice";
import { ReviewView } from "@/components/voice/ReviewView";
import { SessionHeader } from "@/components/voice/SessionHeader";
import { SessionContext } from "@/components/voice/SessionContext";
import { SetupView } from "@/components/voice/SetupView";
import { roundConversationMessages } from "@/lib/aiTranscript";
import {
  cancelAudio,
  createSpeechRecognition,
  hasAudioPlayback,
  hasSpeechRecognition,
  playAudioBlob,
  type SpeechRecognitionLike,
} from "@/lib/speech";
import {
  createVoiceRound,
  endVoiceRound,
  getArgumentOptions,
  getBackendHealth,
  synthesizeLiveAudio,
  submitVoiceTurnStream,
  type ArgumentOptionsPayload,
  type ArgumentOption,
  type Debrief,
  type RoundState,
  type VoiceDifficulty,
  type VoicePersona,
} from "@/lib/voiceBackend";

export default function Home() {
  const [persona, setPersona] = useState<VoicePersona>("difficult_client");
  const [difficulty, setDifficulty] = useState<VoiceDifficulty>("live");
  const [round, setRound] = useState<RoundState | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingUserText, setPendingUserText] = useState("");
  const [streamingAssistantText, setStreamingAssistantText] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [speechAvailable, setSpeechAvailable] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "ready" | "error">("checking");
  const [backendRuntime, setBackendRuntime] = useState("unknown");
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const [argumentOptions, setArgumentOptions] = useState<ArgumentOption[]>([]);
  const [argumentGrounding, setArgumentGrounding] = useState<Omit<ArgumentOptionsPayload, "options"> | null>(null);
  const [argumentOptionsError, setArgumentOptionsError] = useState("");
  const [argumentOptionsLoading, setArgumentOptionsLoading] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionTokenRef = useRef(0);
  const audioTokenRef = useRef(0);

  useEffect(() => {
    const checkId = window.setTimeout(() => {
      setVoiceAvailable(hasSpeechRecognition());
      setSpeechAvailable(hasAudioPlayback());
    }, 0);
    return () => window.clearTimeout(checkId);
  }, []);

  useEffect(() => {
    let cancelled = false;
    getBackendHealth()
      .then((health) => {
        if (cancelled) return;
        setBackendRuntime(health.runtime);
        setBackendStatus(health.configured && health.status === "ok" ? "ready" : "error");
      })
      .catch(() => {
        if (!cancelled) setBackendStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const lastReply = round?.messages.filter((message) => message.role === "opponent").at(-1)?.text ?? "";
  const transcriptMessages = useMemo(
    () => roundConversationMessages(round, pendingUserText, streamingAssistantText),
    [pendingUserText, round, streamingAssistantText],
  );

  async function startSession() {
    const sessionToken = sessionTokenRef.current + 1;
    sessionTokenRef.current = sessionToken;
    setBusy(true);
    setError("");
    setDebrief(null);
    try {
      const next = await createVoiceRound(persona, difficulty);
      if (sessionTokenRef.current !== sessionToken) return;
      setRound(next);
      void loadArgumentOptions(next.id);
      void speak(next.messages.at(-1)?.text ?? "", sessionToken);
    } catch (caught) {
      setError(toError(caught));
    } finally {
      if (sessionTokenRef.current === sessionToken) setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(draft);
  }

  async function send(text: string) {
    const cleaned = text.trim();
    if (!cleaned) return;
    if (!round?.id) {
      setError("Start a credential-backed voice drill before sending a move.");
      return;
    }

    const sessionToken = sessionTokenRef.current;
    setBusy(true);
    setError("");
    setDraft("");
    setPendingUserText(cleaned);
    setStreamingAssistantText("");
    try {
      const result = await submitVoiceTurnStream(round.id, cleaned, (delta) => {
        setStreamingAssistantText((current) => `${current}${delta}`);
      });
      setRound(result.round);
      setPendingUserText("");
      setStreamingAssistantText("");
      void loadArgumentOptions(result.round.id);
      void speak(result.round.messages.at(-1)?.text ?? "", sessionToken);
    } catch (caught) {
      setPendingUserText("");
      setStreamingAssistantText("");
      setDraft(cleaned);
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  function toggleListening() {
    if (!voiceAvailable || busy) return;
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = createSpeechRecognition();
    if (!recognition) return;
    recognition.lang = "en-GB";
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setDraft(transcript);
      void send(transcript);
    };
    recognition.onerror = () => {
      setError("Microphone capture failed. The backend text path is still available.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setError("");
    try {
      recognition.start();
      setListening(true);
    } catch {
      setError("Microphone could not start. The backend text path is still available.");
      setListening(false);
    }
  }

  async function finish() {
    if (!round?.id) {
      setError("Start a backend round before ending the drill.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setDebrief(await endVoiceRound(round.id));
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function loadArgumentOptions(roundId: string) {
    setArgumentOptionsLoading(true);
    setArgumentOptionsError("");
    try {
      const payload = await getArgumentOptions(roundId);
      setArgumentOptions(payload.options);
      setArgumentGrounding({
        tools_used: payload.tools_used,
        sources: payload.sources,
        grounding_note: payload.grounding_note,
      });
    } catch (caught) {
      setArgumentOptions([]);
      setArgumentGrounding(null);
      setArgumentOptionsError(toError(caught));
    } finally {
      setArgumentOptionsLoading(false);
    }
  }

  function backToSetup() {
    sessionTokenRef.current += 1;
    audioTokenRef.current += 1;
    cancelAudio(audioRef.current);
    audioRef.current = null;
    setRound(null);
    setDraft("");
    setPendingUserText("");
    setStreamingAssistantText("");
    setArgumentOptions([]);
    setArgumentGrounding(null);
    setArgumentOptionsError("");
    setArgumentOptionsLoading(false);
    setDebrief(null);
    setError("");
    setListening(false);
    setSpeaking(false);
  }

  async function speak(text: string, expectedSessionToken = sessionTokenRef.current) {
    if (!text.trim()) return;
    const audioToken = audioTokenRef.current + 1;
    audioTokenRef.current = audioToken;
    if (!hasAudioPlayback()) {
      setSpeaking(false);
      setError("Audio playback is not available in this browser.");
      return;
    }

    setSpeaking(true);
    setError("");
    try {
      const audio = await synthesizeLiveAudio(text);
      if (sessionTokenRef.current !== expectedSessionToken || audioTokenRef.current !== audioToken) return;
      audioRef.current = playAudioBlob(audio, audioRef.current, {
        onEnd: () => {
          if (audioTokenRef.current === audioToken) setSpeaking(false);
        },
        onError: () => {
          if (audioTokenRef.current !== audioToken) return;
          setSpeaking(false);
          setError("Gemini Live audio playback failed. Use Speak again or check browser audio permissions.");
        },
        onStart: () => {
          if (audioTokenRef.current === audioToken) setSpeaking(true);
        },
      });
      if (!audioRef.current) {
        setSpeaking(false);
        setError("Gemini Live audio playback is not available in this browser.");
      }
    } catch (caught) {
      if (audioTokenRef.current !== audioToken) return;
      setSpeaking(false);
      setError(toError(caught));
    }
  }

  if (!round) {
    return (
      <SetupView
        backendRuntime={backendRuntime}
        backendStatus={backendStatus}
        busy={busy}
        difficulty={difficulty}
        error={error}
        onDifficultyChange={setDifficulty}
        onPersonaChange={setPersona}
        onStart={() => void startSession()}
        persona={persona}
        voiceAvailable={voiceAvailable}
      />
    );
  }

  if (debrief) {
    return (
      <ReviewView
        debrief={debrief}
        onBackToChat={() => setDebrief(null)}
        onNewSession={backToSetup}
        round={round}
      />
    );
  }

  return (
    <main className="chat-shell">
      <SessionHeader difficulty={difficulty} onBackToSetup={backToSetup} persona={persona} round={round} />
      <section className="session-body">
        <div className="chat-column">
          <section className="chat-scroll">
            <ChatTranscript
              messages={transcriptMessages}
              emptyTitle="No backend round"
              emptyDescription="Start a voice drill to load the credential-backed sparring partner."
            />
          </section>
          <footer className="chat-footer">
            <ErrorNotice message={error} />
            <Composer
              busy={busy}
              draft={draft}
              listening={listening}
              onDraftChange={setDraft}
              onFinish={() => void finish()}
              onReplay={() => void speak(lastReply)}
              onSubmit={submit}
              onToggleListening={toggleListening}
              speaking={speaking}
              speechAvailable={speechAvailable}
              voiceAvailable={voiceAvailable}
            />
          </footer>
        </div>
        <SessionContext
          argumentOptions={argumentOptions}
          argumentOptionsError={argumentOptionsError}
          argumentGrounding={argumentGrounding}
          argumentOptionsLoading={argumentOptionsLoading}
          difficulty={difficulty}
          onRefreshArgumentOptions={() => void loadArgumentOptions(round.id)}
          persona={persona}
          round={round}
        />
      </section>
    </main>
  );
}

function toError(error: unknown) {
  return error instanceof Error ? error.message : "Unknown voice backend error.";
}
