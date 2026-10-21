export type PasswordLoginRequest = {
  email: string;
  password: string;
};

export type VerifyTotpRequest = {
  code: string;
};

export type StepUpRequest = {
  code: string;
  reason: string;
};
