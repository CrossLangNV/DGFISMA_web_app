// This file can be replaced during build by using the `fileReplacements` array.
// `ng build --prod` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

// See env.js under /assets
// According to https://pumpingco.de/blog/environment-variables-angular-docker/
export const environment = {
  ANGULAR_PRODUCTION: window['env']['ANGULAR_PRODUCTION'],
  ANGULAR_APPVERSION: window['env']['APP_VERSION'],
  ANGULAR_DJANGO_API_URL: window['env']['ANGULAR_DJANGO_API_URL'],
  ANGULAR_DJANGO_API_GLOSSARY_URL:
    window['env']['ANGULAR_DJANGO_API_GLOSSARY_URL'],
  ANGULAR_DJANGO_API_RO_URL: window['env']['ANGULAR_DJANGO_API_RO_URL'],
  ANGULAR_DJANGO_API_DBLOGGING_URL: window['env']['ANGULAR_DJANGO_API_DBLOGGING_URL'],
  ANGULAR_DJANGO_API_GLOSSARY_ANNOTATIONS_URL:
    window['env']['ANGULAR_DJANGO_API_GLOSSARY_ANNOTATIONS_URL'],
  ANGULAR_DJANGO_API_RO_ANNOTATIONS_URL:
    window['env']['ANGULAR_DJANGO_API_RO_ANNOTATIONS_URL'],
  ANGULAR_DJANGO_API_ADMIN_URL: window['env']['ANGULAR_DJANGO_API_ADMIN_URL'],
  ANGULAR_DJANGO_AUTH_URL: window['env']['ANGULAR_DJANGO_AUTH_URL'],
  ANGULAR_GOOGLE_CLIENT_ID: window['env']['ANGULAR_GOOGLE_CLIENT_ID'],
  ANGULAR_DJANGO_CLIENT_ID: window['env']['ANGULAR_DJANGO_CLIENT_ID'],
  ANGULAR_DJANGO_CLIENT_SECRET: window['env']['ANGULAR_DJANGO_CLIENT_SECRET'],
  APP_VERSION: window['env']['APP_VERSION'],
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/dist/zone-error';  // Included with Angular CLI.
