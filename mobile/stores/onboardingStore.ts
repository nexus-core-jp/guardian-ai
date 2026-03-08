import { create } from 'zustand';

interface OnboardingState {
  homeLat: number;
  homeLng: number;
  homeAddress: string;
  schoolId: string;
  schoolName: string;
  schoolLat: number;
  schoolLng: number;
  childName: string;
  childGrade: number | undefined;
  gpsDevice: string;

  setHomeLocation: (lat: number, lng: number, address: string) => void;
  setSchool: (id: string, name: string, lat: number, lng: number) => void;
  setChild: (name: string, grade: number | undefined) => void;
  setGpsDevice: (device: string) => void;
  reset: () => void;
}

const initialState = {
  homeLat: 0,
  homeLng: 0,
  homeAddress: '',
  schoolId: '',
  schoolName: '',
  schoolLat: 0,
  schoolLng: 0,
  childName: '',
  childGrade: undefined as number | undefined,
  gpsDevice: 'none',
};

export const useOnboardingStore = create<OnboardingState>((set) => ({
  ...initialState,

  setHomeLocation: (lat, lng, address) =>
    set({ homeLat: lat, homeLng: lng, homeAddress: address }),

  setSchool: (id, name, lat, lng) =>
    set({ schoolId: id, schoolName: name, schoolLat: lat, schoolLng: lng }),

  setChild: (name, grade) =>
    set({ childName: name, childGrade: grade }),

  setGpsDevice: (device) =>
    set({ gpsDevice: device }),

  reset: () => set(initialState),
}));
