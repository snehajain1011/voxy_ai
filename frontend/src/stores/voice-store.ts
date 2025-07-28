import { create } from "zustand";
import { ServiceType } from "~/types/services";

const GRADIENT_COLORS = [
  "linear-gradient(45deg, #8b5cf6, #ec4899, #ffffff, #3b82f6)",
  "linear-gradient(45deg, #3b82f6, #10b981, #ffffff, #f59e0b)",
  "linear-gradient(45deg, #ec4899, #f97316, #ffffff, #8b5cf6)",
  "linear-gradient(45deg, #10b981, #3b82f6, #ffffff, #f43f5e)",
  "linear-gradient(45deg, #f43f5e, #f59e0b, #ffffff, #10b981)",
];

export interface Voice {
  id: string;
  name: string;
  gradientColors: string;
  service: ServiceType;
}

const voices: Voice[] = [
  {
    id: "andreas",
    name: "Andreas",
    gradientColors: GRADIENT_COLORS[0]!,
    service: "styletts2",
  },
  {
    id: "woman",
    name: "Woman",
    gradientColors: GRADIENT_COLORS[1]!,
    service: "styletts2",
  },
  {
    id: "andreas",
    name: "Andreas",
    gradientColors: GRADIENT_COLORS[0]!,
    service: "seedvc",
  },
  {
    id: "woman",
    name: "Woman",
    gradientColors: GRADIENT_COLORS[1]!,
    service: "seedvc",
  },
  {
    id: "trump",
    name: "Trump",
    gradientColors: GRADIENT_COLORS[2]!,
    service: "seedvc",
  },
];

const defaultStyleTTS2Voice =
  voices.find((v) => v.service === "styletts2") ?? null;
const defaultSeedVCVoice = voices.find((v) => v.service === "seedvc") ?? null;

interface VoiceState {
  voices: Voice[];
  selectedVoices: Record<ServiceType, Voice | null>;
  getVoices: (service: ServiceType) => Voice[];
  getSelectedVoice: (service: ServiceType) => Voice | null;
  selectVoice: (service: ServiceType, voice: string) => void;
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  voices: voices,
  selectedVoices: {
    styletts2: defaultStyleTTS2Voice,
    seedvc: defaultSeedVCVoice,
    "make-an-audio": null,
  },
  getVoices: (service) => {
    return get().voices.filter((voice) => voice.service === service);
  },
  getSelectedVoice: (service) => {
    return get().selectedVoices[service];
  },
  selectVoice: (service, voiceId) => {
    const serviceVoices = get().voices.filter(
      (voice) => voice.service === service,
    );

    const selectedVoice =
      serviceVoices.find((voice) => voice.id === voiceId) || serviceVoices[0];

    set((state) => ({
      selectedVoices: {
        ...state.selectedVoices,
        [service]: selectedVoice,
      },
    }));
  },
}));
