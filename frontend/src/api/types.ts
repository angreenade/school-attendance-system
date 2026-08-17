export interface StudentOut {
  id: number;
  student_id: string;
  first_name: string;
  last_name: string;
  grade: string | null;
  homeroom: string | null;
  photo_path: string | null;
  active: boolean;
  is_enrolled_for_recognition: boolean;
  consent_given: boolean;
}

export interface LocationOut {
  id: number;
  name: string;
  location_type: string;
  kiosk_key: string;
}

export interface ClassSectionOut {
  id: number;
  name: string;
  term: string;
  teacher_name: string | null;
  location_id: number | null;
  scheduled_start: string;
  scheduled_days: string;
}

export interface AttendanceLogOut {
  id: number;
  student_id: number;
  student_name: string;
  student_school_id: string;
  location_id: number;
  location_name: string;
  class_section_id: number | null;
  class_section_name: string | null;
  timestamp: string;
  status: "on_time" | "late";
  match_confidence: number;
}

export interface DailyStat {
  date: string;
  on_time: number;
  late: number;
  total: number;
}

export interface SummaryStats {
  total_scans: number;
  unique_students: number;
  on_time_rate: number;
  late_rate: number;
  daily: DailyStat[];
}

export interface ScanResult {
  matched: boolean;
  student_id?: string;
  student_name?: string;
  location_name?: string;
  timestamp?: string;
  status?: "on_time" | "late";
  confidence?: number;
  message: string;
  duplicate: boolean;
}
