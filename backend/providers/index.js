// Provider registry — add a new backend by importing it here and adding to PROVIDERS.
import * as stackai from "./stackai.js";
import * as optimate from "./optimate.js";

const PROVIDERS = [stackai, optimate];

export function getProvider(id) {
  return PROVIDERS.find((p) => p.id === id) ?? null;
}

export function listProviders() {
  return PROVIDERS.map((p) => ({ id: p.id, label: p.label, available: p.isAvailable() }));
}
