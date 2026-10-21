import { auditApi } from './audit.endpoint';
import { authApi } from './auth.endpoint';
import { copilotApi } from './copilot.endpoint';
import { memberApi } from './member.endpoint';
import { toolApi } from './tool.endpoint';
import { visionApi } from './vision.endpoint';

export * from './auth.endpoint';
export * from './copilot.endpoint';
export * from './tool.endpoint';
export * from './member.endpoint';
export * from './audit.endpoint';
export * from './vision.endpoint';

export const consoleApi = {
  ...authApi,
  ...copilotApi,
  ...memberApi,
  ...auditApi,
  ...toolApi,
  ...visionApi,
};
