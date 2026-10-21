export type WorkspacePersona = 'all' | 'admin' | 'ml' | 'labeling' | 'analytics';

export interface PersonaConfig {
  id: WorkspacePersona;
  titleKey: 'all' | 'admin' | 'ml' | 'labeling' | 'analytics';
  descKey: 'allDesc' | 'adminDesc' | 'mlDesc' | 'labelingDesc' | 'analyticsDesc';
  defaultPath: string;
  badge: string;
}
