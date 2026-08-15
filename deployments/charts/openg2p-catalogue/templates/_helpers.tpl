{{- define "catalogue.fullname" -}}
{{- include "common.names.fullname" . -}}
{{- end -}}

{{- define "catalogue.apiName" -}}
{{- printf "%s-api" (include "catalogue.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "catalogue.serviceAccountName" -}}
{{- if .Values.catalogueAPI.serviceAccount.create -}}
{{- default (include "catalogue.apiName" .) .Values.catalogueAPI.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.catalogueAPI.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "catalogue.labels" -}}
app.kubernetes.io/name: {{ include "catalogue.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}

{{- define "catalogue.selectorLabels" -}}
app.kubernetes.io/name: {{ include "catalogue.apiName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

