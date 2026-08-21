pipeline {

    agent any

    environment {

        // ==========================================
        // AWS
        // ==========================================

        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = '361646636271'


        // ==========================================
        // ECR
        // ==========================================

        ECR_REPOSITORY = 'myapp'

        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

        IMAGE_URI = "${ECR_REGISTRY}/${ECR_REPOSITORY}:build-${BUILD_NUMBER}"


        // ==========================================
        // ECS
        // ==========================================

        ECS_CLUSTER = 'myapp-cluster'

        ECS_SERVICE = 'myapp-task-service'

        ECS_TASK_FAMILY = 'myapp-task'


        // ==========================================
        // ECS IAM ROLES
        // ==========================================

        ECS_TASK_ROLE = 'arn:aws:iam::361646636271:role/myappECSTaskRole'

        ECS_EXECUTION_ROLE = 'arn:aws:iam::361646636271:role/ecsTaskExecutionRole'


        // ==========================================
        // RDS
        // ==========================================

        RDS_ENDPOINT = 'myapp-db.cexc2s0ku32a.us-east-1.rds.amazonaws.com'

        RDS_PORT = '3306'


        // ==========================================
        // ALB
        // ==========================================

        ALB_NAME = 'myapp-alb'

        ALB_HEALTH_PATH = '/health'
    }


    stages {


        // =========================================================
        // 1. BUILD DOCKER IMAGE
        // =========================================================

        stage('Build Docker Image') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Building Docker Image"
                    echo "======================================"

                    docker build \
                        --platform linux/amd64 \
                        -t myapp:build-${BUILD_NUMBER} .

                    echo "Docker image created:"
                    docker images myapp
                '''
            }
        }


        // =========================================================
        // 2. RUN APPLICATION LOCALLY
        // =========================================================

        stage('Run Application') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Running Application"
                    echo "======================================"

                    docker rm -f myapp-jenkins-test 2>/dev/null || true

                    docker run -d \
                        --platform linux/amd64 \
                        --name myapp-jenkins-test \
                        --network devops-net \
                        -p 8082:8080 \
                        myapp:build-${BUILD_NUMBER}

                    echo "Application container started."

                    docker ps
                '''
            }
        }


        // =========================================================
        // 3. TEST APPLICATION LOCALLY
        // =========================================================

        stage('Test Application') {

            steps {

                sh '''
                    echo "======================================"
                    echo "Testing Application"
                    echo "======================================"

                    docker run --rm \
                        --platform linux/amd64 \
                        --network devops-net \
                        python:3.12-slim \
                        python3 -c "
import urllib.request
response = urllib.request.urlopen(
    'http://myapp-jenkins-test:8080/health'
)
print(response.read().decode())
"

                    echo "Local application test successful."
                '''
            }
        }


        // =========================================================
        // 4. TEST AWS AUTHENTICATION
        // =========================================================

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

                        echo "AWS authentication successful."
                    '''
                }
            }
        }


        // =========================================================
        // 5. LOGIN TO ECR
        // =========================================================

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


        // =========================================================
        // 6. PUSH IMAGE TO ECR
        // =========================================================

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

                        echo "======================================"
                        echo "Image pushed successfully"
                        echo "======================================"

                        echo "${IMAGE_URI}"
                    '''
                }
            }
        }


        // =========================================================
        // 7. PREPARE ECS TASK DEFINITION
        // =========================================================

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
                        echo "Container Image:"
                        echo "--------------------------------------"

                        jq -r \
                            '.containerDefinitions[]
                            | select(.name == "myapp")
                            | .image' \
                            new-task-definition.json


                        echo "--------------------------------------"
                        echo "Task Role:"
                        echo "--------------------------------------"

                        jq -r \
                            '.taskRoleArn' \
                            new-task-definition.json


                        echo "--------------------------------------"
                        echo "Execution Role:"
                        echo "--------------------------------------"

                        jq -r \
                            '.executionRoleArn' \
                            new-task-definition.json


                        echo "--------------------------------------"
                        echo "Database Configuration:"
                        echo "--------------------------------------"

                        jq -r \
                            '.containerDefinitions[]
                            | select(.name == "myapp")
                            | .environment' \
                            new-task-definition.json
                    '''
                }
            }
        }


        // =========================================================
        // 8. REGISTER ECS TASK DEFINITION
        // =========================================================

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

                        echo "Registered task definition:"
                        echo "${NEW_TASK_DEFINITION}"


                        echo "${NEW_TASK_DEFINITION}" \
                            > new-task-definition-arn.txt
                    '''
                }
            }
        }


        // =========================================================
        // 9. DEPLOY TO ECS
        // =========================================================

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


                        echo "======================================"
                        echo "ECS deployment triggered"
                        echo "======================================"

                        echo "Task Definition:"
                        echo "${NEW_TASK_DEFINITION}"
                    '''
                }
            }
        }


        // =========================================================
        // 10. WAIT FOR ECS DEPLOYMENT
        // =========================================================

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


        // =========================================================
        // 11. VERIFY ECS DEPLOYMENT
        // =========================================================

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
                            --query 'services[0].{
                                Status:status,
                                Desired:desiredCount,
                                Running:runningCount,
                                Pending:pendingCount,
                                TaskDefinition:taskDefinition,
                                ExecuteCommand:enableExecuteCommand
                            }' \
                            --output table
                    '''
                }
            }
        }


        // =========================================================
        // 12. GET ALB DNS
        // =========================================================

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

                        echo "ALB DNS: ${env.ALB_DNS}"
                    }
                }
            }
        }


        // =========================================================
        // 13. VERIFY ALB TARGET HEALTH
        // =========================================================

        stage('Verify ALB Target Health') {

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
                        echo "Target Health:"
                        echo "--------------------------------------"

                        aws elbv2 describe-target-health \
                            --target-group-arn ${TARGET_GROUP_ARN} \
                            --region ${AWS_REGION} \
                            --output table


                        TARGET_STATE=$(aws elbv2 describe-target-health \
                            --target-group-arn ${TARGET_GROUP_ARN} \
                            --region ${AWS_REGION} \
                            --query 'TargetHealthDescriptions[0].TargetHealth.State' \
                            --output text)


                        echo "Target State:"
                        echo "${TARGET_STATE}"


                        if [ "${TARGET_STATE}" != "healthy" ]; then
                            echo "ALB target is NOT healthy."
                            exit 1
                        fi


                        echo "ALB target is healthy."
                    '''
                }
            }
        }


        // =========================================================
        // 14. VERIFY APPLICATION THROUGH ALB
        // =========================================================

        stage('Verify Application through ALB') {

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
                        echo "Verifying Application through ALB"
                        echo "======================================"

                        echo "ALB DNS:"
                        echo "${ALB_DNS}"


                        echo "--------------------------------------"
                        echo "Testing /health"
                        echo "--------------------------------------"


                        HEALTH_RESPONSE=$(curl -s \
                            --fail \
                            "http://${ALB_DNS}${ALB_HEALTH_PATH}")


                        echo "Health Response:"
                        echo "${HEALTH_RESPONSE}"


                        if [ "${HEALTH_RESPONSE}" != "OK" ]; then

                            echo "Application health check FAILED."

                            exit 1

                        fi


                        echo "Health endpoint successful."


                        echo "--------------------------------------"
                        echo "Testing Application"
                        echo "--------------------------------------"


                        APP_RESPONSE=$(curl -s \
                            --fail \
                            "http://${ALB_DNS}/")


                        echo "Application Response:"
                        echo "${APP_RESPONSE}"


                        if [ -z "${APP_RESPONSE}" ]; then

                            echo "Application returned empty response."

                            exit 1

                        fi


                        echo "--------------------------------------"
                        echo "APPLICATION VERIFICATION SUCCESSFUL"
                        echo "--------------------------------------"
                    '''
                }
            }
        }
    }


    // =========================================================
    // POST ACTIONS
    // =========================================================

    post {

        success {

            echo "======================================"
            echo "PIPELINE SUCCESS"
            echo "======================================"

            echo "Application successfully deployed."

            echo "ECR Image:"
            echo "${IMAGE_URI}"

            echo "ECS Cluster:"
            echo "${ECS_CLUSTER}"

            echo "ECS Service:"
            echo "${ECS_SERVICE}"

            echo "ALB:"
            echo "http://${ALB_DNS}"
        }


        failure {

            echo "======================================"
            echo "PIPELINE FAILED"
            echo "======================================"

            echo "Check the failed stage above."
        }


        always {

            sh '''
                echo "======================================"
                echo "Cleaning up Jenkins Docker container"
                echo "======================================"

                docker rm -f myapp-jenkins-test 2>/dev/null || true
            '''
        }
    }
}