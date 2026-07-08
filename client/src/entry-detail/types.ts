export interface EntryReading {
  jyutping: string;
  code0243: string;
  code02493: string;
  initials: string[];
  finals: string[];
}

export interface EntryDetailModel {
  literal: string;
  length: number;
  corpusWeight: number;
  readings: EntryReading[];
  sources: string[];
  syns: string[];
  ants: string[];
}