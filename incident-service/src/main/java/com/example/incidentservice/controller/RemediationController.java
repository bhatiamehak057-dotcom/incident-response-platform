package com.example.incidentservice.controller;

import com.example.incidentservice.model.RemediationDecision;
import com.example.incidentservice.service.RemediationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/incidents")
public class RemediationController {

    private final RemediationService remediationService;

    public RemediationController(RemediationService remediationService) {
        this.remediationService = remediationService;
    }

    //One API because it's one business operation.
    //Multiple Kafka topics because the resulting events have different downstream meanings and processing.
    @PostMapping("/{id}/remediation")
    public ResponseEntity<RemediationDecision> decideRemediation(
            @PathVariable String id,
            @RequestBody RemediationDecision decision) {

        decision.setIncidentId(id);

        remediationService.processDecision(decision);

        return ResponseEntity.ok(decision);
    }
}