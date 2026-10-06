// Hand-written mirrors of the Pydantic models in backend/models + routers.
// Nothing infers across the HTTP boundary — when a Pydantic model changes, change it here too.

export type Role = "super_admin" | "admin" | "gestor" | "funcionario";
export type RecordType = "entrada" | "inicio_intervalo" | "fim_intervalo" | "saida";
export type AdjustmentStatus = "pendente" | "aprovada" | "rejeitada" | "cancelada";
export type ScheduleKind = "fixa" | "12x36" | "6x1" | "5x2";
export type HolidayKind = "nacional" | "estadual" | "municipal" | "facultativo";
export type BankDirection = "credito" | "debito" | "zerado";
export type AlertKind =
  | "saida_nao_registrada"
  | "sem_registro"
  | "intervalo_aberto"
  | "jornada_incompleta"
  | "solicitacao_pendente";

// routers/auth.py :: MeOut
export interface Me {
  id: string;
  name: string;
  email: string;
  role: Role;
  company_id: string;
  company_name: string;
  timezone: string;
  employee_id: string | null;
}

// models/records.py :: TimeRecordOut
export interface TimeRecord {
  id: string;
  company_id: string;
  employee_id: string;
  type: RecordType;
  type_label: string;
  timestamp: string;
  timezone: string;
  hhmm: string;
  local_date: string;
  origin: string;
  status: string;
  observacao: string | null;
  adjusted: boolean;
  created_at: string;
}

// models/records.py :: PunchStatusOut
export interface PunchStatus {
  server_time: string;
  server_hhmm: string;
  local_date: string;
  timezone: string;
  employee_name: string;
  schedule_name: string | null;
  schedule_label: string | null;
  next_type: RecordType | null;
  next_label: string | null;
  status_label: string;
  records: TimeRecord[];
  worked_hhmm: string | null;
  expected_hhmm: string | null;
}

// models/records.py :: AdjustmentOut
export interface Adjustment {
  id: string;
  company_id: string;
  employee_id: string;
  employee_name: string;
  target_date: string;
  type: RecordType;
  type_label: string;
  requested_time: string;
  previous_time: string | null;
  reason: string;
  status: AdjustmentStatus;
  decided_by_name: string | null;
  decision_note: string | null;
  decided_at: string | null;
  created_at: string;
}

// models/employees.py :: EmployeeOut
export interface Employee {
  id: string;
  company_id: string;
  user_id: string | null;
  name: string;
  cpf: string;
  cpf_masked: string;
  matricula: string;
  email: string | null;
  phone: string | null;
  cargo: string | null;
  department: string | null;
  schedule_id: string | null;
  schedule_name: string | null;
  status: string;
  hired_at: string | null;
  created_at: string;
}

// models/schedules.py :: ScheduleOut
export interface Schedule {
  id: string;
  company_id: string;
  name: string;
  entrada: string;
  inicio_intervalo: string;
  fim_intervalo: string;
  saida: string;
  tolerance_minutes: number;
  work_days: number[];
  kind: ScheduleKind;
  cycle_anchor: string | null;
  cycle_on_days: number | null;
  cycle_off_days: number | null;
  expected_hhmm: string | null;
  created_at: string;
}

// models/reports.py :: DaySlot / TimesheetDay / TimesheetSummary / TimesheetOut
export interface DaySlot {
  timestamp: string | null;
  hhmm: string | null;
}

export interface TimesheetDay {
  date: string;
  weekday: string;
  is_workday: boolean;
  holiday_name: string | null;
  schedule_name: string | null;
  entrada: DaySlot;
  inicio_intervalo: DaySlot;
  fim_intervalo: DaySlot;
  saida: DaySlot;
  worked_minutes: number | null;
  worked_hhmm: string | null;
  expected_minutes: number;
  expected_hhmm: string | null;
  delay_minutes: number;
  delay_hhmm: string | null;
  overtime_minutes: number | null;
  overtime_hhmm: string | null;
  balance_minutes: number | null;
  balance_hhmm: string | null;
  status: string;
  justified: boolean;
}

export interface TimesheetSummary {
  total_worked_minutes: number;
  total_worked_hhmm: string | null;
  total_expected_minutes: number;
  total_expected_hhmm: string | null;
  total_balance_minutes: number;
  total_balance_hhmm: string | null;
  total_overtime_minutes: number;
  total_overtime_hhmm: string | null;
  total_delay_minutes: number;
  total_delay_hhmm: string | null;
  faltas: number;
  incompletas: number;
  feriados: number;
}

export interface Timesheet {
  employee_id: string;
  employee_name: string;
  matricula: string | null;
  department: string | null;
  schedule_name: string | null;
  timezone: string;
  start: string;
  end: string;
  days: TimesheetDay[];
  summary: TimesheetSummary;
}

// models/reports.py :: DashboardOut
export interface Dashboard {
  company_name: string;
  local_date: string;
  server_time: string;
  employees_active: number;
  present_now: number;
  on_interval: number;
  absent: number;
  delayed: number;
  incomplete_days: number;
  pending_requests: number;
  overtime_hhmm: string;
  balance_hhmm: string;
  today_records: number;
  holiday_name: string | null;
  alerts_total: number;
  alerts_high: number;
  hours_bank_hhmm: string;
}

// routers/records.py :: live_board row
export interface LiveBoardRow {
  employee_id: string;
  employee_name: string;
  department: string | null;
  state: "ausente" | "trabalhando" | "intervalo" | "encerrado";
  entrada: string | null;
  saida: string | null;
  worked_hhmm: string | null;
  delay_minutes: number;
  delay_hhmm: string | null;
}

// models/reports.py :: AuditOut
export interface AuditLog {
  id: string;
  company_id: string;
  actor_name: string;
  actor_role: string;
  action: string;
  resource: string;
  resource_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip: string | null;
  created_at: string;
}

// models/reports.py :: ReportRow / ReportOut
export interface ReportRow {
  employee_id: string;
  employee_name: string;
  matricula: string | null;
  department: string | null;
  worked_hhmm: string;
  expected_hhmm: string;
  balance_hhmm: string;
  overtime_hhmm: string;
  delay_hhmm: string;
  faltas: number;
  incompletas: number;
}

export interface Report {
  kind: string;
  start: string;
  end: string;
  rows: ReportRow[];
}

// models/calendar.py :: HolidayOut
export interface Holiday {
  id: string;
  company_id: string;
  date: string;
  name: string;
  kind: HolidayKind;
  weekday: string;
  created_at: string;
}

// models/calendar.py :: HolidayImportOut
export interface HolidayImport {
  year: number;
  imported: number;
  skipped: number;
  holidays: Holiday[];
}

// models/calendar.py :: AssignmentOut
export interface Assignment {
  id: string;
  company_id: string;
  employee_id: string;
  employee_name: string;
  schedule_id: string;
  schedule_name: string;
  start_date: string;
  end_date: string | null;
  note: string | null;
  active: boolean;
  created_at: string;
}

// models/hoursbank.py :: HoursBankMonth
export interface HoursBankMonth {
  competence: string;
  label: string;
  worked_minutes: number;
  worked_hhmm: string | null;
  expected_minutes: number;
  expected_hhmm: string | null;
  balance_minutes: number;
  balance_hhmm: string | null;
  overtime_minutes: number;
  overtime_hhmm: string | null;
  faltas: number;
  incompletas: number;
  closed: boolean;
  closed_at: string | null;
  closed_by_name: string | null;
  recalculated_balance_minutes: number | null;
}

// models/hoursbank.py :: HoursBankTotals
export interface HoursBankTotals {
  accumulated_minutes: number;
  accumulated_hhmm: string | null;
  credit_minutes: number;
  credit_hhmm: string | null;
  debit_minutes: number;
  debit_hhmm: string | null;
  to_compensate_minutes: number;
  to_compensate_hhmm: string | null;
  direction: BankDirection;
  closed_months: number;
}

// models/hoursbank.py :: HoursBankOut
export interface HoursBank {
  employee_id: string;
  employee_name: string;
  matricula: string | null;
  department: string | null;
  months: HoursBankMonth[];
  totals: HoursBankTotals;
}

// models/hoursbank.py :: HoursBankBoardRow / HoursBankBoardOut
export interface HoursBankBoardRow {
  employee_id: string;
  employee_name: string;
  matricula: string | null;
  department: string | null;
  current_competence: string;
  current_balance_minutes: number;
  current_balance_hhmm: string | null;
  accumulated_minutes: number;
  accumulated_hhmm: string | null;
  to_compensate_hhmm: string | null;
  direction: BankDirection;
  closed_months: number;
}

export interface HoursBankBoard {
  competence: string;
  label: string;
  months_considered: number;
  rows: HoursBankBoardRow[];
}

// models/hoursbank.py :: CloseCompetenceOut
export interface CloseCompetence {
  competence: string;
  label: string;
  closed: number;
  reopened: boolean;
}

// models/hoursbank.py :: Alert / AlertsOut
export interface Alert {
  employee_id: string;
  employee_name: string;
  department: string | null;
  kind: AlertKind;
  severity: "alta" | "media" | "baixa";
  title: string;
  detail: string;
  date: string;
  reference_hhmm: string | null;
}

export interface Alerts {
  local_date: string;
  server_time: string;
  total: number;
  high: number;
  alerts: Alert[];
}
