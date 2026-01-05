// ============================================
// Jenkinsfile - Continuous Deployment Pipeline
// ============================================
// This pipeline handles deployment of Yojana-AI to EC2 instances
// Triggered by GitHub Actions after successful CI build
// ============================================

pipeline {
    agent any
    
    // ============================================
    // Environment Variables
    // ============================================
    environment {
        // AWS Configuration
        AWS_REGION = 'ap-south-1'
        ECR_REGISTRY = credentials('ecr-registry-url')
        
        // Application Configuration
        APP_NAME = 'yojana-ai'
        DEPLOYMENT_DIR = '/opt/yojana-ai'
        
        // Deployment Server (EC2)
        APP_SERVER_IP = credentials('app-server-ip')
        APP_SERVER_USER = 'ec2-user'
        SSH_KEY = credentials('app-server-ssh-key')
        
        // Docker Compose
        COMPOSE_FILE = 'docker-compose.yml'
        
        // Health Check
        HEALTH_ENDPOINT = 'http://localhost:8000/health'
        MAX_HEALTH_RETRIES = 30
        HEALTH_CHECK_INTERVAL = 2
        
        // Rollback
        BACKUP_TAG = "${APP_NAME}-previous"
    }
    
    // ============================================
    // Build Parameters
    // ============================================
    parameters {
        string(
            name: 'IMAGE_TAG',
            defaultValue: 'latest',
            description: 'Docker image tag to deploy (e.g., abc1234 or latest)'
        )
        string(
            name: 'COMMIT_SHA',
            defaultValue: '',
            description: 'Git commit SHA for tracking'
        )
        booleanParam(
            name: 'SKIP_BACKUP',
            defaultValue: false,
            description: 'Skip creating backup of current deployment'
        )
        booleanParam(
            name: 'RUN_WARMUP',
            defaultValue: true,
            description: 'Run model warmup after deployment'
        )
    }
    
    // ============================================
    // Pipeline Options
    // ============================================
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        ansiColor('xterm')
    }
    
    // ============================================
    // Pipeline Stages
    // ============================================
    stages {
        
        // ============================================
        // Stage 1: Pre-Deployment Validation
        // ============================================
        stage('Pre-Deployment Validation') {
            steps {
                script {
                    echo "⚙️ Starting deployment validation..."
                    
                    // Validate required parameters
                    if (params.IMAGE_TAG == null || params.IMAGE_TAG == '') {
                        error("❌ IMAGE_TAG parameter is required")
                    }
                    
                    echo "📦 Deployment Details:"
                    echo "  - Image Tag: ${params.IMAGE_TAG}"
                    echo "  - Commit SHA: ${params.COMMIT_SHA}"
                    echo "  - Target Server: ${APP_SERVER_IP}"
                    echo "  - Deployment Directory: ${DEPLOYMENT_DIR}"
                    
                    // Test SSH connectivity
                    echo "\n🔍 Testing SSH connectivity to deployment server..."
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            -o ConnectTimeout=10 \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} \
                            'echo "SSH connection successful"'
                    """
                    echo "✓ SSH connectivity verified"
                }
            }
        }
        
        // ============================================
        // Stage 2: Backup Current Deployment
        // ============================================
        stage('Backup Current Deployment') {
            when {
                expression { !params.SKIP_BACKUP }
            }
            steps {
                script {
                    echo "💾 Creating backup of current deployment..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        # Check if application is running
                        if docker ps | grep -q ${APP_NAME}; then
                            echo "Creating backup tag for rollback..."
                            
                            # Get current running image
                            CURRENT_IMAGE=\$(docker inspect ${APP_NAME}-api --format='{{.Config.Image}}')
                            echo "Current image: \$CURRENT_IMAGE"
                            
                            # Tag current image as backup
                            docker tag \$CURRENT_IMAGE ${BACKUP_TAG}
                            echo "✓ Backup created: ${BACKUP_TAG}"
                        else
                            echo "⚠️ No running container found - skipping backup"
                        fi
ENDSSH
                    """
                    
                    echo "✓ Backup completed successfully"
                }
            }
        }
        
        // ============================================
        // Stage 3: Pull New Docker Image
        // ============================================
        stage('Pull Docker Image') {
            steps {
                script {
                    echo "📥 Pulling new Docker image from ECR..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        # Navigate to deployment directory
                        cd ${DEPLOYMENT_DIR}
                        
                        # Login to ECR
                        echo "Authenticating with AWS ECR..."
                        aws ecr get-login-password --region ${AWS_REGION} | \
                            docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        
                        # Pull new image
                        echo "Pulling image: ${ECR_REGISTRY}/${APP_NAME}:${params.IMAGE_TAG}"
                        docker pull ${ECR_REGISTRY}/${APP_NAME}:${params.IMAGE_TAG}
                        
                        # Tag as latest for docker-compose
                        docker tag ${ECR_REGISTRY}/${APP_NAME}:${params.IMAGE_TAG} \
                            ${ECR_REGISTRY}/${APP_NAME}:latest
                        
                        echo "✓ Image pulled successfully"
ENDSSH
                    """
                    
                    echo "✓ Docker image pull completed"
                }
            }
        }
        
        // ============================================
        // Stage 4: Deploy Application
        // ============================================
        stage('Deploy Application') {
            steps {
                script {
                    echo "🚀 Deploying application with docker-compose..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        cd ${DEPLOYMENT_DIR}
                        
                        # Stop current containers gracefully
                        echo "Stopping current containers..."
                        docker-compose down --timeout 30 || true
                        
                        # Start new containers
                        echo "Starting new containers..."
                        docker-compose up -d
                        
                        # Wait for containers to start
                        echo "Waiting for containers to initialize..."
                        sleep 10
                        
                        # Check container status
                        echo "\nContainer Status:"
                        docker-compose ps
                        
                        echo "✓ Containers started successfully"
ENDSSH
                    """
                    
                    echo "✓ Application deployment completed"
                }
            }
        }
        
        // ============================================
        // Stage 5: Health Check
        // ============================================
        stage('Health Check') {
            steps {
                script {
                    echo "🏥 Running health checks..."
                    
                    def healthCheckScript = """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        cd ${DEPLOYMENT_DIR}
                        
                        # Health check with retry logic
                        echo "Checking application health..."
                        RETRY=0
                        MAX_RETRIES=${MAX_HEALTH_RETRIES}
                        
                        while [ \$RETRY -lt \$MAX_RETRIES ]; do
                            echo "Health check attempt \$((\$RETRY + 1))/\$MAX_RETRIES..."
                            
                            # Try health endpoint
                            if docker exec ${APP_NAME}-api curl -f -s ${HEALTH_ENDPOINT} > /dev/null 2>&1; then
                                echo "✓ Application is healthy!"
                                
                                # Get health response
                                HEALTH_RESPONSE=\$(docker exec ${APP_NAME}-api curl -s ${HEALTH_ENDPOINT})
                                echo "Health Response: \$HEALTH_RESPONSE"
                                exit 0
                            fi
                            
                            RETRY=\$((\$RETRY + 1))
                            sleep ${HEALTH_CHECK_INTERVAL}
                        done
                        
                        echo "❌ Health check failed after \$MAX_RETRIES attempts"
                        
                        # Show container logs for debugging
                        echo "\nContainer Logs (last 50 lines):"
                        docker-compose logs --tail=50 api
                        
                        exit 1
ENDSSH
                    """
                    
                    // Execute health check
                    def healthCheckResult = sh(
                        script: healthCheckScript,
                        returnStatus: true
                    )
                    
                    if (healthCheckResult != 0) {
                        error("❌ Application health check failed - initiating rollback")
                    }
                    
                    echo "✓ Health check passed successfully"
                }
            }
        }
        
        // ============================================
        // Stage 6: Model Warmup (Optional)
        // ============================================
        stage('Model Warmup') {
            when {
                expression { params.RUN_WARMUP }
            }
            steps {
                script {
                    echo "🔥 Running model warmup..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        cd ${DEPLOYMENT_DIR}
                        
                        # Run warmup script if it exists
                        if [ -f "scripts/warmup-models.sh" ]; then
                            echo "Executing warmup script..."
                            bash scripts/warmup-models.sh
                            echo "✓ Model warmup completed"
                        else
                            echo "⚠️ Warmup script not found - skipping"
                        fi
ENDSSH
                    """
                    
                    echo "✓ Warmup stage completed"
                }
            }
        }
        
        // ============================================
        // Stage 7: Post-Deployment Verification
        // ============================================
        stage('Post-Deployment Verification') {
            steps {
                script {
                    echo "✅ Running post-deployment verification..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        cd ${DEPLOYMENT_DIR}
                        
                        echo "\n=== Deployment Verification ==="
                        
                        # Container status
                        echo "\n1. Container Status:"
                        docker-compose ps
                        
                        # Resource usage
                        echo "\n2. Resource Usage:"
                        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" ${APP_NAME}-api
                        
                        # Recent logs
                        echo "\n3. Recent Application Logs:"
                        docker-compose logs --tail=20 api
                        
                        # Image info
                        echo "\n4. Deployed Image:"
                        docker inspect ${APP_NAME}-api --format='Image: {{.Config.Image}}'
                        
                        echo "\n✓ Verification completed successfully"
ENDSSH
                    """
                }
            }
        }
    }
    
    // ============================================
    // Post-Build Actions
    // ============================================
    post {
        success {
            script {
                echo """
                ✅ ========================================
                   DEPLOYMENT SUCCESSFUL
                   ========================================
                   Image Tag: ${params.IMAGE_TAG}
                   Commit SHA: ${params.COMMIT_SHA}
                   Server: ${APP_SERVER_IP}
                   Time: ${new Date()}
                   ========================================
                """
                
                // Send success notification (if configured)
                // slackSend(color: 'good', message: "Yojana-AI deployed successfully: ${params.IMAGE_TAG}")
            }
        }
        
        failure {
            script {
                echo """
                ❌ ========================================
                   DEPLOYMENT FAILED
                   ========================================
                   Initiating automatic rollback...
                   ========================================
                """
                
                // Attempt rollback to previous version
                if (!params.SKIP_BACKUP) {
                    echo "♻️ Rolling back to previous version..."
                    
                    sh """
                        ssh -i ${SSH_KEY} \
                            -o StrictHostKeyChecking=no \
                            ${APP_SERVER_USER}@${APP_SERVER_IP} << 'ENDSSH'
                        
                        cd ${DEPLOYMENT_DIR}
                        
                        # Stop failed containers
                        docker-compose down --timeout 30 || true
                        
                        # Restore backup image
                        if docker images | grep -q ${BACKUP_TAG}; then
                            echo "Restoring backup image..."
                            docker tag ${BACKUP_TAG} ${ECR_REGISTRY}/${APP_NAME}:latest
                            
                            # Start with backup image
                            docker-compose up -d
                            
                            echo "✓ Rollback completed"
                        else
                            echo "❌ No backup found - manual intervention required"
                        fi
ENDSSH
                    """
                }
                
                // Send failure notification
                // slackSend(color: 'danger', message: "Yojana-AI deployment failed: ${params.IMAGE_TAG}")
            }
        }
        
        always {
            script {
                // Cleanup
                echo "🧹 Cleaning up..."
                
                // Archive deployment logs
                sh """
                    echo "Deployment completed at: \$(date)" > deployment-summary.txt
                    echo "Image Tag: ${params.IMAGE_TAG}" >> deployment-summary.txt
                    echo "Commit SHA: ${params.COMMIT_SHA}" >> deployment-summary.txt
                    echo "Build Status: ${currentBuild.result}" >> deployment-summary.txt
                """
                
                archiveArtifacts artifacts: 'deployment-summary.txt', fingerprint: true
            }
        }
    }
}
