import { environment } from './environment';

declare let ENV_VARS: {[key: string]: string};

export const Environment = Object.assign(environment, ENV_VARS);
