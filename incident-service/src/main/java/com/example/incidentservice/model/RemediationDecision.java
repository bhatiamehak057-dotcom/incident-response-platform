package com.example.incidentservice.model;

public class RemediationDecision {

    private String incidentId;
    private String action;
    private String service;
    private RemediationDecisionType decision;

    public RemediationDecision() {
    }

    public String getIncidentId() {
        return incidentId;
    }

    public void setIncidentId(String incidentId) {
        this.incidentId = incidentId;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public RemediationDecisionType getDecision() {
        return decision;
    }

    public void setDecision(RemediationDecisionType decision) {
        this.decision = decision;
    }
}