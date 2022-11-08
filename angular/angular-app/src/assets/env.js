(function (window) {
  window["env"] = window["env"] || {};

  // Environment variables
  window["env"]["ANGULAR_PRODUCTION"] = "true";
  window["env"]["ANGULAR_DJANGO_API_URL"] =
    "http://localhost:8000/searchapp/api";
  window["env"]["ANGULAR_DJANGO_API_GLOSSARY_URL"] =
    "http://localhost:8000/glossary/api";
  window["env"]["ANGULAR_DJANGO_API_RO_URL"] =
    "http://localhost:8000/obligations/api";
  window["env"]["ANGULAR_DJANGO_API_DBLOGGING_URL"] =
    "http://localhost:8000/dblogging/api";
  window["env"]["ANGULAR_DJANGO_API_GLOSSARY_ANNOTATIONS_URL"] =
    "http://localhost:8000/glossary/api/annotations";
  window["env"]["ANGULAR_DJANGO_API_RO_ANNOTATIONS_URL"] =
    "http://localhost:8000/obligations/api/annotations";
  window["env"]["ANGULAR_DJANGO_API_ADMIN_URL"] =
    "http://localhost:8000/admin/api";
  window["env"]["ANGULAR_DJANGO_AUTH_URL"] = "http://localhost:8000/auth";
  window["env"]["ANGULAR_GOOGLE_CLIENT_ID"] = "";
  window["env"]["ANGULAR_DJANGO_CLIENT_ID"] = "";
  window["env"]["ANGULAR_DJANGO_CLIENT_SECRET"] = "";
  window["env"]["APP_VERSION"] = "1.0.0-development";

  // window["env"]["ANGULAR_DJANGO_API_URL"] =
  //   "https://django.dgfisma.crosslang.com/searchapp/api";
  // window["env"]["ANGULAR_DJANGO_API_ADMIN_URL"] =
  //   "https://django.dgfisma.crosslang.com/admin/api";
  // window["env"]["ANGULAR_DJANGO_AUTH_URL"] =
  //   "https://django.dgfisma.crosslang.com/auth";
})(this);
