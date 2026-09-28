package com.example.incidentservice.model;

public class Incident {

    private String id;
    private String service;
    private String severity;
    private String error;

    public Incident() {
    }

    public Incident(String id, String service, String severity, String error) {
        this.id = id;
        this.service = service;
        this.severity = severity;
        this.error = error;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public String getSeverity() {
        return severity;
    }

    public void setSeverity(String severity) {
        this.severity = severity;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }
}