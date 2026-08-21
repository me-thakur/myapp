pipeline {

    agent any

    environment {

        // ==============================
        // AWS
        // ==============================
        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = '361646636271'

        // ==============================
        // ECR
        // ==============================
        ECR_REPOSITORY = 'myapp'
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI = "${ECR_REGISTRY}/${ECR_REPOSITORY}:build-${BUILD_NUMBER}"

        // ==============================
        // ECS
        // ==============================
        ECS_CLUSTER = 'myapp-cluster'
        ECS_SERVICE = 'myapp-task-service'
        ECS_TASK_FAMILY = 'myapp-task'

        ECS_TASK_ROLE = 'arn:aws:iam::361646636271:role/myappECSTaskRole'
        ECS_EXECUTION_ROLE = 'arn:aws:iam::361646636271:role/ecsTaskExecutionRole'

        // ==============================
        // RDS
        // ==============================
        RDS_ENDPOINT = 'myapp-db.cexc2s0ku32a.us-east-1.rds.amazonaws.com'
        RDS_PORT = '3306'

        // ==============================
        // ALB
        // ==============================
        ALB_NAME = 'myapp-alb'
        HEALTH_PATH = '/health'
    }


    stages {

        // ============================================================
        // 1. BUILD DOCKER IMAGE
        // ============================================================

        stage('Build Docker Image') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Building Docker Image"
                    echo "======================================"

                    docker buildx build \
                        --platform linux/amd64 \
                        -t myapp:build-${BUILD_NUMBER} \
			--load \
			.
                '''
            }
        }


        // ============================================================
        // 2. RUN APPLICATION LOCALLY
        // ============================================================

        stage('Run Application') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Running Application Locally"
                    echo "======================================"

                    docker rm -f myapp-jenkins-test 2>/dev/null || true

                    docker run -d \
                        --platform linux/amd64 \
                        --name myapp-jenkins-test \
                        --network devops-net \
                        -p 8082:8080 \
                        myapp:build-${BUILD_NUMBER}

                    echo "Application container started."
                '''
            }
        }


        // ============================================================
        // 3. TEST APPLICATION LOCALLY
        // ============================================================

        stage('Test Application') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Testing Application Locally"
                    echo "======================================"

                    echo "Testing /health endpoint..."

                    docker run --rm \
                        --platform linux/amd64 \
                        --network devops-net \
                        python:3.12-slim \
                        python3 -c "import urllib.request; print(urllib.request.urlopen('http://myapp-jenkins-test:8080/health').read().decode())"

                    echo "Local application test successful."
                '''
            }
        }


        // ============================================================
        // 4. TEST AWS AUTHENTICATION
        // ============================================================

        stage('Test AWS Authentication') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Testing AWS Authentication"
                        echo "======================================"

                        aws sts get-caller-identity
                    '''
                }
            }
        }


        // ============================================================
        // 5. LOGIN TO ECR
        // ============================================================

        stage('Login to ECR') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Logging in to ECR"
                        echo "======================================"

                        aws ecr get-login-password \
                            --region ${AWS_REGION} | \
                        docker login \
                            --username AWS \
                            --password-stdin ${ECR_REGISTRY}

                        echo "ECR login successful."
                    '''
                }
            }
        }


        // ============================================================
        // 6. PUSH IMAGE TO ECR
        // ============================================================

        stage('Push Image to ECR') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Pushing Image to ECR"
                        echo "======================================"

                        docker tag \
                            myapp:build-${BUILD_NUMBER} \
                            ${IMAGE_URI}

                        docker push ${IMAGE_URI}

                        echo "Image pushed:"
                        echo "${IMAGE_URI}"
                    '''
                }
            }
        }


        // ============================================================
        // 7. PREPARE ECS TASK DEFINITION
        // ============================================================

        stage('Prepare ECS Task Definition') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Preparing ECS Task Definition"
                        echo "======================================"

                        aws ecs describe-task-definition \
                            --task-definition ${ECS_TASK_FAMILY} \
                            --region ${AWS_REGION} \
                            --query 'taskDefinition' \
                            > task-definition.json

                        echo "Current task definition downloaded."

                        jq \
                            --arg IMAGE "${IMAGE_URI}" \
                            --arg TASK_ROLE "${ECS_TASK_ROLE}" \
                            --arg EXECUTION_ROLE "${ECS_EXECUTION_ROLE}" \
                            --arg DB_HOST "${RDS_ENDPOINT}" \
                            --arg DB_PORT "${RDS_PORT}" \
                            '
                            .containerDefinitions |=
                            map(
                                if .name == "myapp"
                                then
                                    .image = $IMAGE
                                    |
                                    .environment = [
                                        {
                                            "name": "DB_HOST",
                                            "value": $DB_HOST
                                        },
                                        {
                                            "name": "DB_PORT",
                                            "value": $DB_PORT
                                        }
                                    ]
                                else .
                                end
                            )
                            |
                            .taskRoleArn = $TASK_ROLE
                            |
                            .executionRoleArn = $EXECUTION_ROLE
                            |
                            del(
                                .taskDefinitionArn,
                                .revision,
                                .status,
                                .requiresAttributes,
                                .compatibilities,
                                .registeredAt,
                                .registeredBy
                            )
                            ' task-definition.json > new-task-definition.json

                        echo "New task definition prepared."

                        echo "--------------------------------------"
                        echo "Image:"
                        jq -r '.containerDefinitions[] | select(.name == "myapp") | .image' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Task Role:"
                        jq -r '.taskRoleArn' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Execution Role:"
                        jq -r '.executionRoleArn' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Database Configuration:"
                        jq -r '.containerDefinitions[] | select(.name == "myapp") | .environment' new-task-definition.json
                    '''
                }
            }
        }


        // ============================================================
        // 8. REGISTER NEW ECS TASK DEFINITION
        // ============================================================

        stage('Register ECS Task Definition') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Registering ECS Task Definition"
                        echo "======================================"

                        NEW_TASK_DEFINITION=$(aws ecs register-task-definition \
                            --cli-input-json file://new-task-definition.json \
                            --region ${AWS_REGION} \
                            --query 'taskDefinition.taskDefinitionArn' \
                            --output text)

                        echo "Registered:"
                        echo "${NEW_TASK_DEFINITION}"

                        echo "${NEW_TASK_DEFINITION}" > new-task-definition-arn.txt
                    '''
                }
            }
        }


        // ============================================================
        // 9. DEPLOY TO ECS
        // ============================================================

        stage('Deploy to ECS') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Deploying to ECS"
                        echo "======================================"

                        NEW_TASK_DEFINITION=$(cat new-task-definition-arn.txt)

                        aws ecs update-service \
                            --cluster ${ECS_CLUSTER} \
                            --service ${ECS_SERVICE} \
                            --task-definition ${NEW_TASK_DEFINITION} \
                            --enable-execute-command \
                            --region ${AWS_REGION}

                        echo "ECS deployment triggered."

                        echo "Task Definition:"
                        echo "${NEW_TASK_DEFINITION}"
                    '''
                }
            }
        }


        // ============================================================
        // 10. WAIT FOR ECS DEPLOYMENT
        // ============================================================

        stage('Wait for ECS Deployment') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Waiting for ECS Deployment"
                        echo "======================================"

                        aws ecs wait services-stable \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION}

                        echo "ECS service is stable."
                    '''
                }
            }
        }


        // ============================================================
        // 11. VERIFY ECS SERVICE
        // ============================================================

        stage('Verify ECS Deployment') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Verifying ECS Deployment"
                        echo "======================================"

                        aws ecs describe-services \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION} \
                            --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDefinition:taskDefinition,ExecuteCommand:enableExecuteCommand}' \
                            --output table

                        DESIRED=$(aws ecs describe-services \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION} \
                            --query 'services[0].desiredCount' \
                            --output text)

                        RUNNING=$(aws ecs describe-services \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION} \
                            --query 'services[0].runningCount' \
                            --output text)

                        if [ "$DESIRED" -ne "$RUNNING" ]; then
                            echo "ECS service is NOT healthy."
                            echo "Desired: $DESIRED"
                            echo "Running: $RUNNING"
                            exit 1
                        fi

                        echo "ECS service is healthy."
                    '''
                }
            }
        }


        // ============================================================
        // 12. CHECK ALB TARGET HEALTH
        // ============================================================

        stage('Check ALB Target Health') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    sh '''
                        echo "======================================"
                        echo "Checking ALB Target Health"
                        echo "======================================"

                        TARGET_GROUP_ARN=$(aws ecs describe-services \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION} \
                            --query 'services[0].loadBalancers[0].targetGroupArn' \
                            --output text)

                        echo "Target Group:"
                        echo "${TARGET_GROUP_ARN}"

                        echo "--------------------------------------"
                        echo "Waiting for at least one healthy target..."
                        echo "--------------------------------------"

                        HEALTHY=false

                        for i in $(seq 1 30)
                        do

                            echo "Health check attempt $i/30"

                            aws elbv2 describe-target-health \
                                --target-group-arn ${TARGET_GROUP_ARN} \
                                --region ${AWS_REGION} \
                                --output table

                            HEALTHY_COUNT=$(aws elbv2 describe-target-health \
                                --target-group-arn ${TARGET_GROUP_ARN} \
                                --region ${AWS_REGION} \
                                --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' \
                                --output text)

                            echo "Healthy targets: ${HEALTHY_COUNT}"

                            if [ "${HEALTHY_COUNT}" -ge 1 ]; then
                                HEALTHY=true
                                break
                            fi

                            echo "No healthy target yet. Waiting 10 seconds..."
                            sleep 10

                        done

                        if [ "${HEALTHY}" != "true" ]; then

                            echo "======================================"
                            echo "ALB TARGET HEALTH CHECK FAILED"
                            echo "======================================"

                            echo "Final target health:"

                            aws elbv2 describe-target-health \
                                --target-group-arn ${TARGET_GROUP_ARN} \
                                --region ${AWS_REGION} \
                                --output table

                            exit 1
                        fi

                        echo "======================================"
                        echo "ALB TARGET IS HEALTHY"
                        echo "======================================"
                    '''
                }
            }
        }


        // ============================================================
        // 13. GET ALB DNS
        // ============================================================

        stage('Get ALB DNS') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {

                    script {

                        env.ALB_DNS = sh(
                            script: '''
                                aws elbv2 describe-load-balancers \
                                    --names ${ALB_NAME} \
                                    --region ${AWS_REGION} \
                                    --query 'LoadBalancers[0].DNSName' \
                                    --output text
                            ''',
                            returnStdout: true
                        ).trim()

                        echo "ALB DNS:"
                        echo "${env.ALB_DNS}"
                    }
                }
            }
        }


        // ============================================================
        // 14. VERIFY APPLICATION THROUGH ALB
        // ============================================================

        stage('Verify Application through ALB') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Verifying Application through ALB"
                    echo "======================================"

                    echo "ALB:"
                    echo "http://${ALB_DNS}"

                    echo "--------------------------------------"
                    echo "Testing /health"
                    echo "--------------------------------------"

                    HEALTH_RESPONSE=$(curl -s \
                        --max-time 10 \
                        "http://${ALB_DNS}${HEALTH_PATH}")

                    echo "Health Response:"
                    echo "${HEALTH_RESPONSE}"

                    if [ "${HEALTH_RESPONSE}" != "OK" ]; then

                        echo "ALB health endpoint FAILED."

                        exit 1
                    fi

                    echo "ALB health endpoint successful."

                    echo "--------------------------------------"
                    echo "Testing application"
                    echo "--------------------------------------"

                    APP_RESPONSE=$(curl -s \
                        --max-time 10 \
                        "http://${ALB_DNS}/")

                    echo "Application Response:"
                    echo "${APP_RESPONSE}"

                    if echo "${APP_RESPONSE}" | grep -q "Application is running"; then

                        echo "Application verification successful."

                    else

                        echo "Application verification FAILED."

                        exit 1
                    fi
                '''
            }
        }


        // ============================================================
        // 15. FINAL DEPLOYMENT SUMMARY
        // ============================================================

        stage('Deployment Summary') {

            steps {

                echo "======================================"
                echo "DEPLOYMENT SUCCESSFUL"
                echo "======================================"

                echo "Build Number: ${BUILD_NUMBER}"
                echo "Docker Image: ${IMAGE_URI}"
                echo "ECS Cluster: ${ECS_CLUSTER}"
                echo "ECS Service: ${ECS_SERVICE}"
                echo "ALB DNS: http://${ALB_DNS}"
                echo "Health URL: http://${ALB_DNS}${HEALTH_PATH}"
            }
        }
    }


    // ================================================================
    // POST ACTIONS
    // ================================================================

    post {

        success {

            echo "======================================"
            echo "PIPELINE SUCCESS"
            echo "======================================"

            echo "Application successfully built, tested,"
            echo "pushed to ECR, deployed to ECS,"
            echo "validated through ALB and verified."
        }

        failure {

            echo "======================================"
            echo "PIPELINE FAILED"
            echo "======================================"

            echo "Check the failed stage above."
        }

        always {

            sh '''
                docker rm -f myapp-jenkins-test 2>/dev/null || true
            '''
        }
    }
}
