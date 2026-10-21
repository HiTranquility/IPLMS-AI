export type InviteMemberRequest = {
  email: string;
  displayName: string;
  reason: string;
};

export type RoleChangeRequest = {
  memberId: string;
  role: string;
  reason: string;
  grant: boolean;
};
