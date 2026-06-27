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
  synthesizeLiveAudio,
  submitVoiceTurn,
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
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [speechAvailable, setSpeechAvailable] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const [argumentOptions, setArgumentOptions] = useState<ArgumentOption[]>([]);
  const [argumentOptionsError, setArgumentOptionsError] = useState("");
  const [argumentOptionsLoading, setArgumentOptionsLoading] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const checkId = window.setTimeout(() => {
      setVoiceAvailable(hasSpeechRecognition());
      setSpeechAvailable(hasAudioPlayback());
    }, 0);
    return () => window.clearTimeout(checkId);
  }, []);

  const lastReply = round?.messages.filter((message) => message.role === "opponent").at(-1)?.text ?? "";
  const transcriptMessages = useMemo(() => roundConversationMessages(round), [round]);

  async function startSession() {
    setBusy(true);
    setError("");
    setDebrief(null);
    try {
      const next = await createVoiceRound(persona, difficulty);
      setRound(next);
      void loadArgumentOptions(next.id);
      void speak(next.messages.at(-1)?.text ?? "");
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
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

    setBusy(true);
    setError("");
    try {
      const result = await submitVoiceTurn(round.id, cleaned);
      setRound(result.round);
      setDraft("");
      void loadArgumentOptions(result.round.id);
      void speak(result.round.messages.at(-1)?.text ?? "");
    } catch (caught) {
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
      setArgumentOptions(await getArgumentOptions(roundId));
    } catch (caught) {
      setArgumentOptions([]);
      setArgumentOptionsError(toError(caught));
    } finally {
      setArgumentOptionsLoading(false);
    }
  }

  function backToSetup() {
    cancelAudio(audioRef.current);
    audioRef.current = null;
    setRound(null);
    setDraft("");
    setArgumentOptions([]);
    setArgumentOptionsError("");
    setArgumentOptionsLoading(false);
    setDebrief(null);
    setError("");
    setListening(false);
    setSpeaking(false);
  }

  async function speak(text: string) {
    if (!hasAudioPlayback()) {
      setSpeaking(false);
      setError("Audio playback is not available in this browser.");
      return;
    }

    setSpeaking(true);
    setError("");
    try {
      const audio = await synthesizeLiveAudio(text);
      audioRef.current = playAudioBlob(audio, audioRef.current, {
        onEnd: () => setSpeaking(false),
        onError: () => {
          setSpeaking(false);
          setError("Gemini Live audio playback failed. Use Speak again or check browser audio permissions.");
        },
        onStart: () => setSpeaking(true),
      });
      if (!audioRef.current) {
        setSpeaking(false);
        setError("Gemini Live audio playback is not available in this browser.");
      }
    } catch (caught) {
      setSpeaking(false);
      setError(toError(caught));
    }
  }

  if (!round) {
    return (
      <SetupView
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
          argumentOptionsLoading={argumentOptionsLoading}
          difficulty={difficulty}
          onRefreshArgumentOptions={() => void loadArgumentOptions(round.id)}
          onSelectArgument={setDraft}
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
